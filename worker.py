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
TELEGRAM_CHAT_IDS = os.getenv("TELEGRAM_CHAT_IDS", "").split(",")

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
            destino TEXT,
            fecha TEXT,
            mejor_precio REAL,
            mejor_aerolinea TEXT,
            total_ofertas INTEGER,
            ofertas_baratas INTEGER,
            detalle_ofertas TEXT
        )
    """)
    conn.commit()
    conn.close()


def guardar_precio(busqueda_nombre, destino, mejor_precio, mejor_aerolinea, total, baratas, detalle):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO precios (busqueda, destino, fecha, mejor_precio, mejor_aerolinea, total_ofertas, ofertas_baratas, detalle_ofertas) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (busqueda_nombre, destino, datetime.now().strftime("%Y-%m-%d %H:%M"), mejor_precio, mejor_aerolinea, total, baratas, json.dumps(detalle)),
    )
    conn.commit()
    conn.close()


def obtener_todos_los_precios():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT busqueda, destino, fecha, mejor_precio, mejor_aerolinea, total_ofertas, ofertas_baratas, detalle_ofertas FROM precios ORDER BY id")
    rows = c.fetchall()
    conn.close()

    resultado = {}
    for row in rows:
        busqueda, destino, fecha, precio, aerolinea, total, baratas, detalle_json = row
        if busqueda not in resultado:
            resultado[busqueda] = []

        detalle = []
        if detalle_json:
            try:
                detalle = json.loads(detalle_json)
            except:
                pass

        resultado[busqueda].append({
            "fecha": fecha,
            "precio": precio,
            "aerolinea": aerolinea,
            "totalOfertas": total,
            "ofertasBaratas": baratas,
            "ofertas": detalle,
            "destino": destino or "",
        })
    return resultado


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
    # --- Filipinas + PNG ---
    {
        "nombre": "Filipinas ANTES del tour",
        "destino": "Filipinas + PNG",
        "origen": "EZE",
        "destino_code": "MNL",
        "ida_fecha": "2026-07-28",
        "vuelta_fecha": "2026-08-22",
        "precio_maximo": 1500,
    },
    {
        "nombre": "Filipinas DESPUES del tour",
        "destino": "Filipinas + PNG",
        "origen": "EZE",
        "destino_code": "MNL",
        "ida_fecha": "2026-08-10",
        "vuelta_fecha": "2026-09-03",
        "precio_maximo": 1500,
    },
    # --- Londres ---
    {
        "nombre": "Londres fechas tempranas",
        "destino": "Londres",
        "origen": "EZE",
        "destino_code": "LHR",
        "ida_fecha": "2026-09-09",
        "vuelta_fecha": "2026-10-01",
        "precio_maximo": 1000,
    },
    {
        "nombre": "Londres fechas centrales",
        "destino": "Londres",
        "origen": "EZE",
        "destino_code": "LHR",
        "ida_fecha": "2026-09-11",
        "vuelta_fecha": "2026-10-03",
        "precio_maximo": 1000,
    },
    {
        "nombre": "Londres fechas tardias",
        "destino": "Londres",
        "origen": "EZE",
        "destino_code": "LHR",
        "ida_fecha": "2026-09-13",
        "vuelta_fecha": "2026-10-05",
        "precio_maximo": 1000,
    },
]


def generar_links(busqueda):
    ida = busqueda["ida_fecha"]
    vuelta = busqueda["vuelta_fecha"]
    origen = busqueda["origen"]
    destino = busqueda["destino_code"]

    ida_yymmdd = ida.replace("-", "")[2:]
    vuelta_yymmdd = vuelta.replace("-", "")[2:]

    skyscanner_destinos = {"MNL": "mnl", "LHR": "lhr"}
    skyscanner_dest = skyscanner_destinos.get(destino, destino.lower())

    skyscanner = f"https://www.skyscanner.com.ar/transport/flights/buea/{skyscanner_dest}/{ida_yymmdd}/{vuelta_yymmdd}/?adults=1"
    google = f"https://www.google.com/travel/flights?q=Flights+to+{destino}+from+{origen}+on+{ida}+through+{vuelta}&curr=USD"
    kayak = f"https://www.kayak.com/flights/{origen}-{destino}/{ida}/{vuelta}?sort=bestflight_a&fs=stops=0"

    return skyscanner, google, kayak


def extraer_detalle_oferta(offer):
    precio = float(offer["total_amount"])
    aerolinea = offer["owner"]["name"]
    tramos = []
    duracion_total_min = 0

    for s in offer["slices"]:
        segmentos = s["segments"]
        n_stops = len(segmentos) - 1
        origen = segmentos[0]["origin"]["iata_code"]
        destino_final = segmentos[-1]["destination"]["iata_code"]

        escalas = []
        duracion_tramo_min = 0
        aerolineas_tramo = set()

        for seg in segmentos:
            aerolineas_tramo.add(seg.get("operating_carrier", {}).get("name") or seg.get("marketing_carrier", {}).get("name", ""))
            dur = seg.get("duration", "")
            if dur:
                try:
                    d = dur.replace("PT", "")
                    h = 0
                    m = 0
                    if "H" in d:
                        parts = d.split("H")
                        h = int(parts[0])
                        d = parts[1] if len(parts) > 1 else ""
                    if "M" in d:
                        m = int(d.replace("M", ""))
                    duracion_tramo_min += h * 60 + m
                except:
                    pass

        for seg in segmentos[:-1]:
            escalas.append(seg["destination"]["iata_code"])

        duracion_total_min += duracion_tramo_min
        duracion_texto = f"{duracion_tramo_min // 60}h{duracion_tramo_min % 60:02d}m" if duracion_tramo_min > 0 else ""

        tramos.append({
            "origen": origen,
            "destino": destino_final,
            "escalas": escalas,
            "numEscalas": n_stops,
            "duracion": duracion_texto,
            "duracionMin": duracion_tramo_min,
            "aerolineasTramo": list(aerolineas_tramo),
        })

    duracion_total_texto = f"{duracion_total_min // 60}h{duracion_total_min % 60:02d}m" if duracion_total_min > 0 else ""

    return {
        "precio": precio,
        "aerolinea": aerolinea,
        "tramos": tramos,
        "duracionTotal": duracion_total_texto,
        "duracionTotalMin": duracion_total_min,
    }


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
                {"origin": busqueda["origen"], "destination": busqueda["destino_code"], "departure_date": busqueda["ida_fecha"]},
                {"origin": busqueda["destino_code"], "destination": busqueda["origen"], "departure_date": busqueda["vuelta_fecha"]},
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
    chunks = []
    if len(mensaje) <= 4000:
        chunks = [mensaje]
    else:
        partes = mensaje.split("\n\n")
        chunk = ""
        for parte in partes:
            if len(chunk) + len(parte) + 2 > 4000:
                if chunk:
                    chunks.append(chunk)
                chunk = parte
            else:
                chunk = chunk + "\n\n" + parte if chunk else parte
        if chunk:
            chunks.append(chunk)

    for chat_id in TELEGRAM_CHAT_IDS:
        chat_id = chat_id.strip()
        if not chat_id:
            continue
        for chunk in chunks:
            data = {"chat_id": chat_id, "text": chunk, "disable_web_page_preview": True}
            try:
                resp = requests.post(url, data=data)
                if resp.status_code != 200:
                    print(f"  Error Telegram {chat_id}: {resp.status_code} - {resp.text[:200]}")
                else:
                    print(f"  Telegram OK -> {chat_id}")
            except Exception as e:
                print(f"  Error enviando a {chat_id}: {e}")


def formatear_oferta_tg(offer):
    detalle = extraer_detalle_oferta(offer)
    lineas = [f"USD {detalle['precio']} - {detalle['aerolinea']}"]
    if detalle['duracionTotal']:
        lineas[0] += f" ({detalle['duracionTotal']} total)"
    for t in detalle['tramos']:
        if t['numEscalas'] == 0:
            lineas.append(f"  {t['origen']}->{t['destino']} directo")
        else:
            esc = ', '.join(t['escalas'])
            lineas.append(f"  {t['origen']}->{t['destino']} ({t['numEscalas']} esc: {esc})")
        if t['duracion']:
            lineas[-1] += f" {t['duracion']}"
    return "\n".join(lineas)


def emoji_tendencia(tendencia):
    if tendencia == "BAJANDO":
        return "BAJANDO"
    elif tendencia == "SUBIENDO":
        return "SUBIENDO"
    elif tendencia == "ESTABLE":
        return "ESTABLE"
    return "SIN DATOS"


# ─── MONITOR ───

def ejecutar_monitor():
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"=== Flight Monitor - {ahora} ===\n")

    init_db()
    destinos_resultados = {}

    for busqueda in BUSQUEDAS:
        nombre = busqueda["nombre"]
        destino = busqueda["destino"]
        precio_max = busqueda["precio_maximo"]
        print(f"Buscando: {nombre}...")
        print(f"  Ida: {busqueda['ida_fecha']} / Vuelta: {busqueda['vuelta_fecha']} / Max: USD {precio_max}")

        ofertas = buscar_vuelos(busqueda)
        print(f"  Encontradas: {len(ofertas)} ofertas")

        baratas = sorted(
            [o for o in ofertas if float(o["total_amount"]) <= precio_max],
            key=lambda x: float(x["total_amount"]),
        )
        print(f"  Por debajo de USD {precio_max}: {len(baratas)}")

        mejor_precio = None
        mejor_aerolinea = None
        detalle_baratas = []

        if ofertas:
            mejor = min(ofertas, key=lambda x: float(x["total_amount"]))
            mejor_precio = float(mejor["total_amount"])
            mejor_aerolinea = mejor["owner"]["name"]
            print(f"  Mejor precio: USD {mejor_precio} ({mejor_aerolinea})")

        for oferta in baratas[:10]:
            detalle_baratas.append(extraer_detalle_oferta(oferta))

        if mejor_precio:
            guardar_precio(nombre, destino, mejor_precio, mejor_aerolinea, len(ofertas), len(baratas), detalle_baratas)

        tendencia = detectar_tendencia(nombre)

        if destino not in destinos_resultados:
            destinos_resultados[destino] = {"alertas": [], "tendencias": []}

        if baratas:
            links = generar_links(busqueda)
            destinos_resultados[destino]["alertas"].append((nombre, baratas, links, tendencia, precio_max))
        elif tendencia == "BAJANDO" and mejor_precio:
            links = generar_links(busqueda)
            destinos_resultados[destino]["tendencias"].append((nombre, mejor_precio, mejor_aerolinea, links, precio_max))

        print()

    algo_enviado = False
    for destino, resultados in destinos_resultados.items():
        if not resultados["alertas"] and not resultados["tendencias"]:
            continue

        mensaje = f"FLIGHT MONITOR - {ahora}\n"
        mensaje += f"{destino}\n"
        mensaje += "=" * 30 + "\n\n"

        for nombre, baratas, links, tendencia, precio_max in resultados["alertas"]:
            skyscanner, google, kayak = links
            mensaje += f"{nombre}\n"
            mensaje += f"Tendencia: {emoji_tendencia(tendencia)}\n"
            for oferta in baratas[:3]:
                mensaje += formatear_oferta_tg(oferta) + "\n"
            mensaje += f"\nSkyscanner: {skyscanner}\nGoogle: {google}\nKayak: {kayak}\n\n"

        for nombre, precio, aerolinea, links, precio_max in resultados["tendencias"]:
            skyscanner, google, kayak = links
            mensaje += f"TENDENCIA: {nombre}\n"
            mensaje += f"Precio bajando! Actual: USD {precio} ({aerolinea})\n"
            mensaje += f"\nSkyscanner: {skyscanner}\nGoogle: {google}\nKayak: {kayak}\n\n"

        enviar_telegram(mensaje)
        algo_enviado = True

    if algo_enviado:
        print("ALERTA(S) ENVIADA(S) A TELEGRAM")
    else:
        print("No se encontraron ofertas dentro de los rangos.")

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

    destino_map = {}
    precio_map = {}
    for b in BUSQUEDAS:
        destino_map[b["nombre"]] = b.get("destino", "Sin destino")
        precio_map[b["nombre"]] = b.get("precio_maximo", 1500)

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
            "objetivo": precio_map.get(nombre, 1500),
            "destino": destino_map.get(nombre, "Sin destino"),
        }

    return jsonify(resultado)


@app.route("/api/destinos")
def api_destinos():
    destinos = {}
    for b in BUSQUEDAS:
        dest = b.get("destino", "Sin destino")
        if dest not in destinos:
            destinos[dest] = []
        destinos[dest].append(b["nombre"])
    return jsonify(destinos)


# ─── INICIO ───

if __name__ == "__main__":
    print(f"Worker iniciado - ejecuta cada {INTERVALO_HORAS} horas")
    print(f"API disponible en puerto {PORT}")
    print(f"Telegram destinos: {len([c for c in TELEGRAM_CHAT_IDS if c.strip()])} chat(s)")
    print(f"Busquedas configuradas: {len(BUSQUEDAS)}")
    init_db()

    monitor_thread = threading.Thread(target=loop_monitor, daemon=True)
    monitor_thread.start()

    app.run(host="0.0.0.0", port=PORT)
