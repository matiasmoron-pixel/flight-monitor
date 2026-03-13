import os
import time
import sqlite3
import traceback
import threading
import json
import requests
from datetime import datetime
from flask import Flask, jsonify
from flask_cors import CORS

DUFFEL_TOKEN = os.getenv("DUFFEL_TOKEN")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

PRECIO_MAXIMO = 1500
INTERVALO_HORAS = 6
DB_PATH = "vuelos.db"
PORT = int(os.getenv("PORT", 8080))

# ─── BASE DE DATOS ───

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS precios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            busqueda TEXT,
            fecha TEXT,
            mejor_precio REAL,
            mejor_aerolinea TEXT,
            total_ofertas INTEGER,
            ofertas_baratas INTEGER
        )
    """)
    conn.commit()
    conn.close()


def guardar_precio(busqueda_nombre, mejor_precio, mejor_aerolinea, total, baratas):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO precios (busqueda, fecha, mejor_precio, mejor_aerolinea, total_ofertas, ofertas_baratas) VALUES (?, ?, ?, ?, ?, ?)",
        (busqueda_nombre, datetime.now().strftime("%Y-%m-%d %H:%M"), mejor_precio, mejor_aerolinea, total, baratas),
    )
    conn.commit()
    conn.close()


def obtener_todos_los_precios():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT busqueda, fecha, mejor_precio, mejor_aerolinea, total_ofertas, ofertas_baratas FROM precios ORDER BY id")
    rows = c.fetchall()
    conn.close()

    resultado = {}
    for row in rows:
        busqueda, fecha, precio, aerolinea, total, baratas = row
        if busqueda not in resultado:
            resultado[busqueda] = []
        resultado[busqueda].append({
            "fecha": fecha,
            "precio": precio,
            "aerolinea": aerolinea,
            "totalOfertas": total,
            "ofertasBaratas": baratas,
        })
    return resultado


def obtener_stats(busqueda_nombre):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT mejor_precio FROM precios WHERE busqueda = ? ORDER BY id",
        (busqueda_nombre,),
    )
    precios = [row[0] for row in c.fetchall()]
    conn.close()

    if not precios:
        return None

    return {
        "minimo": min(precios),
        "maximo": max(precios),
        "promedio": round(sum(precios) / len(precios), 2),
        "registros": len(precios),
        "ultimos": precios[-5:],
    }


def detectar_tendencia(busqueda_nombre):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT mejor_precio FROM precios WHERE busqueda = ? ORDER BY id DESC LIMIT 4",
        (busqueda_nombre,),
    )
    precios = [row[0] for row in c.fetchall()]
    conn.close()

    if len(precios) < 4:
        return None

    precios.reverse()
    bajadas = sum(1 for i in range(1, len(precios)) if precios[i] < precios[i - 1])
    if bajadas >= 3:
        return "BAJANDO"

    subidas = sum(1 for i in range(1, len(precios)) if precios[i] > precios[i - 1])
    if subidas >= 3:
        return "SUBIENDO"

    return "ESTABLE"


# ─── BUSQUEDAS ───

BUSQUEDAS = [
    {
        "nombre": "Filipinas ANTES del tour",
        "origen": "EZE",
        "destino": "MNL",
        "ida_fecha": "2026-07-28",
        "vuelta_fecha": "2026-08-22",
    },
    {
        "nombre": "Filipinas DESPUES del tour",
        "origen": "EZE",
        "destino": "MNL",
        "ida_fecha": "2026-08-10",
        "vuelta_fecha": "2026-09-03",
    },
]


def generar_links(busqueda):
    ida = busqueda["ida_fecha"]
    vuelta = busqueda["vuelta_fecha"]
    origen = busqueda["origen"]
    destino = busqueda["destino"]

    ida_yymmdd = ida.replace("-", "")[2:]
    vuelta_yymmdd = vuelta.replace("-", "")[2:]

    skyscanner = f"https://www.skyscanner.com.ar/transport/flights/buea/mnl/{ida_yymmdd}/{vuelta_yymmdd}/?adults=1"
    google = f"https://www.google.com/travel/flights?q=Flights+to+{destino}+from+{origen}+on+{ida}+through+{vuelta}&curr=USD"
    kayak = f"https://www.kayak.com/flights/{origen}-{destino}/{ida}/{vuelta}?sort=bestflight_a&fs=stops=0"

    return skyscanner, google, kayak


def buscar_vuelos(busqueda):
    headers = {
        "Accept-Encoding": "gzip",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Duffel-Version": "v2",
        "Authorization": f"Bearer {DUFFEL_TOKEN}",
    }

    payload = {
        "data": {
            "slices": [
                {"origin": busqueda["origen"], "destination": busqueda["destino"], "departure_date": busqueda["ida_fecha"]},
                {"origin": busqueda["destino"], "destination": busqueda["origen"], "departure_date": busqueda["vuelta_fecha"]},
            ],
            "passengers": [{"type": "adult"}],
        }
    }

    response = requests.post(
        "https://api.duffel.com/air/offer_requests?return_offers=true",
        headers=headers,
        json=payload,
    )

    if response.status_code not in [200, 201]:
        print(f"  Error API: {response.status_code}")
        return []

    data = response.json()["data"]
    return data.get("offers", [])


# ─── TELEGRAM ───

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "HTML", "disable_web_page_preview": True}
    requests.post(url, data=data)


def formatear_oferta(offer):
    price = offer["total_amount"]
    airline = offer["owner"]["name"]
    tramos = []
    for s in offer["slices"]:
        n_stops = len(s["segments"]) - 1
        origin = s["segments"][0]["origin"]["iata_code"]
        dest = s["segments"][-1]["destination"]["iata_code"]
        tramos.append(f"  {origin}->{dest} ({n_stops} escalas)")
    return f"USD {price} - {airline}\n" + "\n".join(tramos)


def emoji_tendencia(tendencia):
    if tendencia == "BAJANDO":
        return "📉 BAJANDO"
    elif tendencia == "SUBIENDO":
        return "📈 SUBIENDO"
    elif tendencia == "ESTABLE":
        return "➡️ ESTABLE"
    return "🆕 SIN DATOS"


# ─── MONITOR ───

def ejecutar_monitor():
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"=== Flight Monitor - {ahora} ===\n")

    init_db()
    alertas_por_busqueda = []
    alerta_tendencia = []

    for busqueda in BUSQUEDAS:
        nombre = busqueda["nombre"]
        print(f"Buscando: {nombre}...")
        print(f"  Ida: {busqueda['ida_fecha']} / Vuelta: {busqueda['vuelta_fecha']}")

        ofertas = buscar_vuelos(busqueda)
        print(f"  Encontradas: {len(ofertas)} ofertas")

        baratas = sorted(
            [o for o in ofertas if float(o["total_amount"]) <= PRECIO_MAXIMO],
            key=lambda x: float(x["total_amount"]),
        )
        print(f"  Por debajo de USD {PRECIO_MAXIMO}: {len(baratas)}")

        mejor_precio = None
        mejor_aerolinea = None
        if ofertas:
            mejor = min(ofertas, key=lambda x: float(x["total_amount"]))
            mejor_precio = float(mejor["total_amount"])
            mejor_aerolinea = mejor["owner"]["name"]
            print(f"  Mejor precio: USD {mejor_precio} ({mejor_aerolinea})")

        if mejor_precio:
            guardar_precio(nombre, mejor_precio, mejor_aerolinea, len(ofertas), len(baratas))

        tendencia = detectar_tendencia(nombre)
        stats = obtener_stats(nombre)

        if tendencia:
            print(f"  Tendencia: {tendencia}")
        if stats:
            print(f"  Stats: min={stats['minimo']}, max={stats['maximo']}, avg={stats['promedio']}, registros={stats['registros']}")

        if baratas:
            links = generar_links(busqueda)
            alertas_por_busqueda.append((nombre, baratas, links, tendencia, stats))
        elif tendencia == "BAJANDO" and mejor_precio:
            links = generar_links(busqueda)
            alerta_tendencia.append((nombre, mejor_precio, mejor_aerolinea, links, stats))

        print()

    if alertas_por_busqueda or alerta_tendencia:
        mensaje = f"<b>✈️ ALERTA DE VUELOS</b>\n{ahora}\n\n"

        for nombre, baratas, links, tendencia, stats in alertas_por_busqueda:
            skyscanner, google, kayak = links
            mensaje += f"<b>{nombre}</b>\n"
            mensaje += f"Tendencia: {emoji_tendencia(tendencia)}\n"
            for oferta in baratas:
                mensaje += formatear_oferta(oferta) + "\n"
            if stats:
                mensaje += f"\n📊 Min: USD {stats['minimo']} | Max: USD {stats['maximo']} | Prom: USD {stats['promedio']} ({stats['registros']} reg)\n"
            mensaje += f"\n<a href='{skyscanner}'>Skyscanner</a> | <a href='{google}'>Google Flights</a> | <a href='{kayak}'>Kayak</a>\n\n"

        for nombre, precio, aerolinea, links, stats in alerta_tendencia:
            skyscanner, google, kayak = links
            mensaje += f"<b>📉 TENDENCIA: {nombre}</b>\n"
            mensaje += f"Precio bajando 3 veces seguidas!\nActual: USD {precio} ({aerolinea})\n"
            if stats:
                mensaje += f"📊 Min: USD {stats['minimo']} | Max: USD {stats['maximo']} | Prom: USD {stats['promedio']}\n"
            mensaje += f"\n<a href='{skyscanner}'>Skyscanner</a> | <a href='{google}'>Google Flights</a> | <a href='{kayak}'>Kayak</a>\n\n"

        enviar_telegram(mensaje)
        print("ALERTA ENVIADA A TELEGRAM")
    else:
        print(f"No se encontraron vuelos por debajo de USD {PRECIO_MAXIMO}.")

    print("\n=== Fin ===")


def loop_monitor():
    while True:
        try:
            print(f"\n--- Ejecutando monitor: {datetime.now().strftime('%Y-%m-%d %H:%M')} ---")
            ejecutar_monitor()
        except Exception as e:
            print(f"Error en ejecucion: {e}")
            traceback.print_exc()

        print(f"Proxima ejecucion en {INTERVALO_HORAS} horas...")
        time.sleep(INTERVALO_HORAS * 3600)


# ─── API PARA DASHBOARD ───

app = Flask(__name__)
CORS(app)


@app.route("/")
def home():
    return jsonify({"status": "ok", "servicio": "Flight Monitor API"})


@app.route("/api/precios")
def api_precios():
    init_db()
    datos = obtener_todos_los_precios()

    resultado = {}
    for nombre, registros in datos.items():
        precios = [r["precio"] for r in registros]
        tendencia = detectar_tendencia(nombre)

        resultado[nombre] = {
            "registros": registros,
            "stats": {
                "minimo": min(precios) if precios else 0,
                "maximo": max(precios) if precios else 0,
                "promedio": round(sum(precios) / len(precios), 2) if precios else 0,
                "total": len(precios),
            },
            "tendencia": tendencia or "SIN DATOS",
            "objetivo": PRECIO_MAXIMO,
        }

    return jsonify(resultado)


# ─── INICIO ───

if __name__ == "__main__":
    print(f"Worker iniciado - ejecuta cada {INTERVALO_HORAS} horas")
    print(f"API disponible en puerto {PORT}")
    init_db()

    monitor_thread = threading.Thread(target=loop_monitor, daemon=True)
    monitor_thread.start()

    app.run(host="0.0.0.0", port=PORT)
