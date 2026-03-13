import os
import time
import traceback
import threading
import json
import requests
import psycopg2
from datetime import datetime
from flask import Flask, jsonify
from flask_cors import CORS

DUFFEL_TOKEN = os.getenv("DUFFEL_TOKEN")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_IDS = os.getenv("TELEGRAM_CHAT_IDS", "").split(",")
DATABASE_URL = os.getenv("DATABASE_URL")

INTERVALO_HORAS = 6
PORT = int(os.getenv("PORT", 8080))
LAST_UPDATE_ID = 0

# ─── BASE DE DATOS (POSTGRES) ───

def get_conn():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS precios (
            id SERIAL PRIMARY KEY,
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
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO precios (busqueda, destino, fecha, mejor_precio, mejor_aerolinea, total_ofertas, ofertas_baratas, detalle_ofertas) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (busqueda_nombre, destino, datetime.now().strftime("%Y-%m-%d %H:%M"), mejor_precio, mejor_aerolinea, total, baratas, json.dumps(detalle)),
    )
    conn.commit()
    conn.close()


def obtener_todos_los_precios():
    conn = get_conn()
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
            "fecha": fecha, "precio": precio, "aerolinea": aerolinea,
            "totalOfertas": total, "ofertasBaratas": baratas,
            "ofertas": detalle, "destino": destino or "",
        })
    return resultado


def detectar_tendencia(busqueda_nombre):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT mejor_precio FROM precios WHERE busqueda = %s ORDER BY id DESC LIMIT 4", (busqueda_nombre,))
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


def obtener_historial(busqueda_nombre):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT mejor_precio FROM precios WHERE busqueda = %s ORDER BY id", (busqueda_nombre,))
    precios = [row[0] for row in c.fetchall()]
    conn.close()
    return precios


# ─── PREDICCION ───

def analizar_compra(busqueda_nombre, precio_actual, precio_maximo):
    precios = obtener_historial(busqueda_nombre)
    if len(precios) < 2:
        return None

    minimo = min(precios)
    maximo = max(precios)
    promedio = sum(precios) / len(precios)
    rango = maximo - minimo if maximo != minimo else 1
    posicion = ((precio_actual - minimo) / rango) * 100 if rango > 0 else 50
    tendencia = detectar_tendencia(busqueda_nombre)

    if precio_actual <= minimo:
        return {"accion": "COMPRA AHORA", "razon": "Precio minimo historico! Nunca estuvo tan bajo.",
                "confianza": "ALTA", "posicion": posicion, "minimo": minimo, "maximo": maximo, "promedio": round(promedio, 2)}
    elif posicion <= 10:
        return {"accion": "COMPRA AHORA", "razon": f"Muy cerca del minimo historico (${minimo}). Solo ${round(precio_actual - minimo, 2)} mas caro.",
                "confianza": "ALTA", "posicion": posicion, "minimo": minimo, "maximo": maximo, "promedio": round(promedio, 2)}
    elif posicion <= 30 and tendencia == "BAJANDO":
        return {"accion": "BUEN MOMENTO", "razon": "Precio bajo y tendencia a la baja.",
                "confianza": "MEDIA", "posicion": posicion, "minimo": minimo, "maximo": maximo, "promedio": round(promedio, 2)}
    elif posicion <= 30:
        return {"accion": "BUEN MOMENTO", "razon": "Precio en zona baja del rango historico.",
                "confianza": "MEDIA", "posicion": posicion, "minimo": minimo, "maximo": maximo, "promedio": round(promedio, 2)}
    elif tendencia == "BAJANDO":
        return {"accion": "ESPERA", "razon": "Precio en zona media pero bajando. Conviene esperar.",
                "confianza": "MEDIA", "posicion": posicion, "minimo": minimo, "maximo": maximo, "promedio": round(promedio, 2)}
    elif tendencia == "SUBIENDO":
        return {"accion": "ATENTO", "razon": "Precio subiendo. Puede convenir comprar pronto.",
                "confianza": "BAJA", "posicion": posicion, "minimo": minimo, "maximo": maximo, "promedio": round(promedio, 2)}
    else:
        return {"accion": "ESPERA", "razon": "Precio en zona media. Monitorear.",
                "confianza": "BAJA", "posicion": posicion, "minimo": minimo, "maximo": maximo, "promedio": round(promedio, 2)}


# ─── BUSQUEDAS ───

BUSQUEDAS = [
    {"nombre": "Filipinas ANTES del tour", "destino": "Filipinas + PNG", "origen": "EZE", "destino_code": "MNL",
     "ida_fecha": "2026-07-28", "vuelta_fecha": "2026-08-22", "precio_maximo": 1500},
    {"nombre": "Filipinas DESPUES del tour", "destino": "Filipinas + PNG", "origen": "EZE", "destino_code": "MNL",
     "ida_fecha": "2026-08-10", "vuelta_fecha": "2026-09-03", "precio_maximo": 1500},
    {"nombre": "Londres fechas tempranas", "destino": "Londres", "origen": "EZE", "destino_code": "LHR",
     "ida_fecha": "2026-09-09", "vuelta_fecha": "2026-10-01", "precio_maximo": 1000},
    {"nombre": "Londres fechas centrales", "destino": "Londres", "origen": "EZE", "destino_code": "LHR",
     "ida_fecha": "2026-09-11", "vuelta_fecha": "2026-10-03", "precio_maximo": 1000},
    {"nombre": "Londres fechas tardias", "destino": "Londres", "origen": "EZE", "destino_code": "LHR",
     "ida_fecha": "2026-09-13", "vuelta_fecha": "2026-10-05", "precio_maximo": 1000},
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
                    h, m = 0, 0
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
        tramos.append({"origen": origen, "destino": destino_final, "escalas": escalas,
                       "numEscalas": n_stops, "duracion": duracion_texto, "duracionMin": duracion_tramo_min,
                       "aerolineasTramo": list(aerolineas_tramo)})
    duracion_total_texto = f"{duracion_total_min // 60}h{duracion_total_min % 60:02d}m" if duracion_total_min > 0 else ""
    return {"precio": precio, "aerolinea": aerolinea, "tramos": tramos,
            "duracionTotal": duracion_total_texto, "duracionTotalMin": duracion_total_min}


def buscar_vuelos(busqueda):
    headers = {"Accept-Encoding": "gzip", "Accept": "application/json", "Content-Type": "application/json",
               "Duffel-Version": "v2", "Authorization": f"Bearer {DUFFEL_TOKEN}"}
    payload = {"data": {"slices": [
        {"origin": busqueda["origen"], "destination": busqueda["destino_code"], "departure_date": busqueda["ida_fecha"]},
        {"origin": busqueda["destino_code"], "destination": busqueda["origen"], "departure_date": busqueda["vuelta_fecha"]},
    ], "passengers": [{"type": "adult"}]}}
    response = requests.post("https://api.duffel.com/air/offer_requests?return_offers=true", headers=headers, json=payload)
    if response.status_code not in [200, 201]:
        print(f"  Error API: {response.status_code}")
        return []
    return response.json()["data"].get("offers", [])


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


def enviar_telegram_a(chat_id, mensaje):
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
    for chunk in chunks:
        data = {"chat_id": chat_id, "text": chunk, "disable_web_page_preview": True}
        try:
            requests.post(url, data=data)
        except:
            pass


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


# ─── BOT INTERACTIVO ───

def procesar_comando(chat_id, texto):
    texto = texto.strip().lower()

    if texto in ["/start", "/help", "hola"]:
        msg = "Flight Monitor Bot\n" + "=" * 25 + "\n\n"
        msg += "Comandos:\n\n"
        msg += "/precios - Mejores precios actuales\n"
        msg += "/buscar - Buscar precios AHORA (~30s)\n"
        msg += "/consejo - Comprar o esperar?\n"
        msg += "/status - Estado del sistema\n"
        enviar_telegram_a(chat_id, msg)

    elif texto == "/precios":
        init_db()
        datos = obtener_todos_los_precios()
        if not datos:
            enviar_telegram_a(chat_id, "Sin datos todavia. Espera a la proxima busqueda.")
            return
        msg = "MEJORES PRECIOS ACTUALES\n" + "=" * 30 + "\n\n"
        destinos_vistos = {}
        for nombre, registros in datos.items():
            if not registros:
                continue
            ultimo = registros[-1]
            busqueda_config = next((b for b in BUSQUEDAS if b["nombre"] == nombre), None)
            destino = busqueda_config["destino"] if busqueda_config else "?"
            if destino not in destinos_vistos:
                destinos_vistos[destino] = []
            destinos_vistos[destino].append((nombre, ultimo))
        for destino, items in destinos_vistos.items():
            msg += f"{destino}\n" + "-" * 20 + "\n"
            mejor = min(items, key=lambda x: x[1]["precio"])
            for nombre, ultimo in items:
                marcador = " << MEJOR" if (nombre, ultimo) == mejor else ""
                msg += f"  {nombre}: USD {ultimo['precio']} ({ultimo['aerolinea']}){marcador}\n"
            msg += f"  Ultima busqueda: {mejor[1]['fecha']}\n\n"
        enviar_telegram_a(chat_id, msg)

    elif texto == "/buscar":
        enviar_telegram_a(chat_id, "Buscando precios... (30-60 segundos)")
        try:
            ejecutar_monitor()
            enviar_telegram_a(chat_id, "Busqueda completada! Usa /precios para ver resultados.")
        except Exception as e:
            enviar_telegram_a(chat_id, f"Error: {e}")

    elif texto == "/consejo":
        init_db()
        datos = obtener_todos_los_precios()
        if not datos:
            enviar_telegram_a(chat_id, "Sin datos suficientes. Necesito al menos 2 busquedas.")
            return
        msg = "CONSEJO DE COMPRA\n" + "=" * 30 + "\n\n"
        for busqueda in BUSQUEDAS:
            nombre = busqueda["nombre"]
            if nombre not in datos or not datos[nombre]:
                continue
            ultimo_precio = datos[nombre][-1]["precio"]
            analisis = analizar_compra(nombre, ultimo_precio, busqueda["precio_maximo"])
            if not analisis:
                continue
            iconos = {"COMPRA AHORA": "🔥", "BUEN MOMENTO": "👍", "ESPERA": "⏳", "ATENTO": "⚠️"}
            icono = iconos.get(analisis["accion"], "")
            msg += f"{icono} {nombre}\n"
            msg += f"  Precio: USD {ultimo_precio}\n"
            msg += f"  Accion: {analisis['accion']} ({analisis['confianza']})\n"
            msg += f"  {analisis['razon']}\n"
            msg += f"  Rango: ${analisis['minimo']} - ${analisis['maximo']} (prom: ${analisis['promedio']})\n\n"
        enviar_telegram_a(chat_id, msg)

    elif texto == "/status":
        init_db()
        datos = obtener_todos_los_precios()
        total_registros = sum(len(r) for r in datos.values())
        msg = "ESTADO DEL SISTEMA\n" + "=" * 25 + "\n\n"
        msg += f"Base de datos: PostgreSQL (persistente)\n"
        msg += f"Busquedas: {len(BUSQUEDAS)}\n"
        msg += f"Registros guardados: {total_registros}\n"
        msg += f"Destinos Telegram: {len([c for c in TELEGRAM_CHAT_IDS if c.strip()])}\n"
        msg += f"Intervalo: cada {INTERVALO_HORAS} horas\n"
        msg += f"Dashboard: https://matiasmoron-pixel.github.io/flight-monitor/\n"
        enviar_telegram_a(chat_id, msg)


def loop_bot():
    global LAST_UPDATE_ID
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    print("Bot de Telegram iniciado - escuchando comandos...")
    while True:
        try:
            params = {"offset": LAST_UPDATE_ID + 1, "timeout": 30}
            resp = requests.get(url, params=params, timeout=35)
            if resp.status_code == 200:
                updates = resp.json().get("result", [])
                for update in updates:
                    LAST_UPDATE_ID = update["update_id"]
                    message = update.get("message", {})
                    chat_id = str(message.get("chat", {}).get("id", ""))
                    texto = message.get("text", "")
                    if chat_id and texto:
                        print(f"  Bot recibio: '{texto}' de {chat_id}")
                        procesar_comando(chat_id, texto)
        except Exception as e:
            print(f"  Error bot: {e}")
            time.sleep(5)


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

        baratas = sorted([o for o in ofertas if float(o["total_amount"]) <= precio_max], key=lambda x: float(x["total_amount"]))
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
            destinos_resultados[destino] = {"alertas": [], "tendencias": [], "compras": []}

        if mejor_precio:
            analisis = analizar_compra(nombre, mejor_precio, precio_max)
            if analisis and analisis["accion"] == "COMPRA AHORA":
                destinos_resultados[destino]["compras"].append((nombre, mejor_precio, mejor_aerolinea, analisis))

        if baratas:
            links = generar_links(busqueda)
            destinos_resultados[destino]["alertas"].append((nombre, baratas, links, tendencia, precio_max))
        elif tendencia == "BAJANDO" and mejor_precio:
            links = generar_links(busqueda)
            destinos_resultados[destino]["tendencias"].append((nombre, mejor_precio, mejor_aerolinea, links, precio_max))

        print()

    algo_enviado = False
    for destino, resultados in destinos_resultados.items():
        if not resultados["alertas"] and not resultados["tendencias"] and not resultados["compras"]:
            continue

        mensaje = f"FLIGHT MONITOR - {ahora}\n{destino}\n" + "=" * 30 + "\n\n"

        for nombre, precio, aerolinea, analisis in resultados["compras"]:
            mensaje += "🔥🔥🔥 COMPRA AHORA 🔥🔥🔥\n"
            mensaje += f"{nombre}\nUSD {precio} ({aerolinea})\n{analisis['razon']}\n"
            mensaje += f"Rango: ${analisis['minimo']} - ${analisis['maximo']} (prom: ${analisis['promedio']})\n\n"

        for nombre, baratas, links, tendencia, precio_max in resultados["alertas"]:
            skyscanner, google, kayak = links
            tend_txt = tendencia if tendencia else "SIN DATOS"
            mensaje += f"{nombre}\nTendencia: {tend_txt}\n"
            for oferta in baratas[:3]:
                mensaje += formatear_oferta_tg(oferta) + "\n"
            mensaje += f"\nSkyscanner: {skyscanner}\nGoogle: {google}\nKayak: {kayak}\n\n"

        for nombre, precio, aerolinea, links, precio_max in resultados["tendencias"]:
            skyscanner, google, kayak = links
            mensaje += f"TENDENCIA: {nombre}\nPrecio bajando! USD {precio} ({aerolinea})\n"
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
    return jsonify({"status": "ok", "servicio": "Flight Monitor API", "db": "PostgreSQL"})


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
        ultimo_precio = precios[-1] if precios else 0
        analisis = analizar_compra(nombre, ultimo_precio, precio_map.get(nombre, 1500)) if len(precios) >= 2 else None

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
            "consejo": analisis,
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
    print(f"Base de datos: PostgreSQL")
    init_db()

    monitor_thread = threading.Thread(target=loop_monitor, daemon=True)
    monitor_thread.start()

    bot_thread = threading.Thread(target=loop_bot, daemon=True)
    bot_thread.start()

    app.run(host="0.0.0.0", port=PORT)
