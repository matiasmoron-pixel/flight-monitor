"""
Flight Monitor v3.0
- SQLite: historial completo de precios
- Detección de tendencia bajista
- Alertas inteligentes (no solo umbral fijo)
- Deploy-ready para Railway/Render
"""

import os
import sqlite3
import logging
import requests
import time
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path

# ─────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────

load_dotenv()

DUFFEL_TOKEN       = os.getenv("DUFFEL_TOKEN")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")

PRECIO_MAXIMO      = 1500    # USD — alerta directa
BAJAS_CONSECUTIVAS = 3       # cuántas bajas seguidas para alertar tendencia
MAX_RETRIES        = 3
RETRY_DELAY        = 10
DB_FILE            = Path("vuelos.db")
LOG_FILE           = Path("flight_monitor.log")

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

# ─────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────
# BASE DE DATOS
# ─────────────────────────────────────────

def init_db():
    """Crea la tabla si no existe."""
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS precios (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                busqueda    TEXT    NOT NULL,
                fecha       TEXT    NOT NULL,
                precio      REAL    NOT NULL,
                aerolinea   TEXT,
                escalas_ida INTEGER,
                escalas_vuelta INTEGER
            )
        """)
        conn.commit()


def guardar_precio(busqueda: str, precio: float, aerolinea: str,
                   escalas_ida: int, escalas_vuelta: int):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            "INSERT INTO precios (busqueda, fecha, precio, aerolinea, escalas_ida, escalas_vuelta) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (busqueda, datetime.now().isoformat(), precio, aerolinea, escalas_ida, escalas_vuelta)
        )
        conn.commit()


def obtener_ultimos_precios(busqueda: str, n: int = 10) -> list[float]:
    """Devuelve los últimos N precios mínimos registrados para esa búsqueda."""
    with sqlite3.connect(DB_FILE) as conn:
        rows = conn.execute(
            "SELECT precio FROM precios WHERE busqueda = ? "
            "ORDER BY fecha DESC LIMIT ?",
            (busqueda, n)
        ).fetchall()
    return [r[0] for r in rows]


def obtener_minimo_historico(busqueda: str) -> float | None:
    with sqlite3.connect(DB_FILE) as conn:
        row = conn.execute(
            "SELECT MIN(precio) FROM precios WHERE busqueda = ?",
            (busqueda,)
        ).fetchone()
    return row[0] if row else None


def obtener_resumen_tendencia(busqueda: str) -> str:
    """Genera texto con estadísticas para el mensaje de Telegram."""
    with sqlite3.connect(DB_FILE) as conn:
        rows = conn.execute(
            "SELECT precio, fecha FROM precios WHERE busqueda = ? "
            "ORDER BY fecha DESC LIMIT 20",
            (busqueda,)
        ).fetchall()

    if not rows:
        return ""

    precios = [r[0] for r in rows]
    minimo  = min(precios)
    maximo  = max(precios)
    promedio = sum(precios) / len(precios)

    return (
        f"  📊 Mín histórico: USD {minimo:.0f} | "
        f"Máx: USD {maximo:.0f} | "
        f"Promedio: USD {promedio:.0f} ({len(precios)} muestras)"
    )


# ─────────────────────────────────────────
# DETECCIÓN DE TENDENCIA
# ─────────────────────────────────────────

def detectar_tendencia_bajista(busqueda: str, precio_actual: float) -> bool:
    """
    Devuelve True si el precio bajó en las últimas N ejecuciones consecutivas.
    Útil para alertar aunque el precio esté sobre el umbral.
    """
    ultimos = obtener_ultimos_precios(busqueda, BAJAS_CONSECUTIVAS + 1)

    if len(ultimos) < BAJAS_CONSECUTIVAS:
        return False

    # ultimos[0] es el más reciente (antes de guardar el actual)
    # Reconstruimos la secuencia con el precio actual incluido
    secuencia = [precio_actual] + ultimos[:BAJAS_CONSECUTIVAS]

    for i in range(len(secuencia) - 1):
        if secuencia[i] >= secuencia[i + 1]:
            return False  # no es bajista en este punto

    return True


def calcular_caida_porcentual(busqueda: str, precio_actual: float) -> float | None:
    """Calcula cuánto bajó respecto al máximo reciente (últimas 20 muestras)."""
    ultimos = obtener_ultimos_precios(busqueda, 20)
    if not ultimos:
        return None
    maximo_reciente = max(ultimos)
    if maximo_reciente == 0:
        return None
    return ((maximo_reciente - precio_actual) / maximo_reciente) * 100


# ─────────────────────────────────────────
# LINKS
# ─────────────────────────────────────────

def generar_links(b: dict) -> tuple[str, str, str]:
    ida     = b["ida_fecha"]
    vuelta  = b["vuelta_fecha"]
    origen  = b["origen"].lower()
    destino = b["destino"].lower()

    ida_yy    = ida.replace("-", "")[2:]
    vuelta_yy = vuelta.replace("-", "")[2:]

    skyscanner = (
        f"https://www.skyscanner.com.ar/transport/flights/{origen}/{destino}/"
        f"{ida_yy}/{vuelta_yy}/?adults=1"
    )
    google = (
        f"https://www.google.com/travel/flights?q=Flights+to+"
        f"{b['destino']}+from+{b['origen']}+on+{ida}+through+{vuelta}&curr=USD"
    )
    kayak = (
        f"https://www.kayak.com/flights/{b['origen']}-{b['destino']}"
        f"/{ida}/{vuelta}?sort=bestflight_a&fs=stops=0"
    )
    return skyscanner, google, kayak


# ─────────────────────────────────────────
# API DUFFEL
# ─────────────────────────────────────────

def buscar_vuelos(busqueda: dict) -> list | None:
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
                {
                    "origin": busqueda["origen"],
                    "destination": busqueda["destino"],
                    "departure_date": busqueda["ida_fecha"],
                },
                {
                    "origin": busqueda["destino"],
                    "destination": busqueda["origen"],
                    "departure_date": busqueda["vuelta_fecha"],
                },
            ],
            "passengers": [{"type": "adult"}],
        }
    }

    for intento in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(
                "https://api.duffel.com/air/offer_requests?return_offers=true",
                headers=headers,
                json=payload,
                timeout=30,
            )
            if response.status_code in [200, 201]:
                return response.json()["data"].get("offers", [])
            log.warning(f"API {response.status_code} — intento {intento}/{MAX_RETRIES}")
            if intento < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
        except requests.exceptions.RequestException as e:
            log.error(f"Error de red intento {intento}: {e}")
            if intento < MAX_RETRIES:
                time.sleep(RETRY_DELAY)

    return None


# ─────────────────────────────────────────
# TELEGRAM
# ─────────────────────────────────────────

def enviar_telegram(mensaje: str):
    url  = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        r = requests.post(url, data=data, timeout=15)
        if r.status_code != 200:
            log.error(f"Telegram error: {r.status_code} — {r.text}")
    except requests.exceptions.RequestException as e:
        log.error(f"Telegram no disponible: {e}")


def notificar_error_api(nombre: str):
    enviar_telegram(
        f"⚠️ <b>Flight Monitor — Error API</b>\n\n"
        f"No se pudo consultar Duffel para:\n<b>{nombre}</b>\n\n"
        f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )


# ─────────────────────────────────────────
# FORMATEO
# ─────────────────────────────────────────

def formatear_oferta(offer: dict) -> str:
    price   = float(offer["total_amount"])
    airline = offer["owner"]["name"]
    tramos  = []
    for s in offer["slices"]:
        n_stops  = len(s["segments"]) - 1
        origin   = s["segments"][0]["origin"]["iata_code"]
        dest     = s["segments"][-1]["destination"]["iata_code"]
        paradas  = "directo" if n_stops == 0 else f"{n_stops} escala{'s' if n_stops > 1 else ''}"
        tramos.append(f"  {origin}→{dest} · {paradas}")
    return f"💰 <b>USD {price:.0f}</b> — {airline}\n" + "\n".join(tramos)


def escalas_de_oferta(offer: dict) -> tuple[int, int]:
    slices = offer["slices"]
    ida    = len(slices[0]["segments"]) - 1 if len(slices) > 0 else 0
    vuelta = len(slices[1]["segments"]) - 1 if len(slices) > 1 else 0
    return ida, vuelta


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

def main():
    init_db()
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M")
    log.info(f"=== Flight Monitor v3 — {ahora} ===")

    alertas_umbral    = []   # precios bajo PRECIO_MAXIMO
    alertas_tendencia = []   # bajando 3 veces seguidas aunque estén sobre umbral
    alertas_minimo    = []   # nuevo mínimo histórico

    for busqueda in BUSQUEDAS:
        nombre = busqueda["nombre"]
        log.info(f"Buscando: {nombre}...")

        ofertas = buscar_vuelos(busqueda)

        if ofertas is None:
            log.error(f"  Fallo total API — {nombre}")
            notificar_error_api(nombre)
            continue

        if not ofertas:
            log.info(f"  Sin resultados")
            continue

        mejor  = min(ofertas, key=lambda x: float(x["total_amount"]))
        precio = float(mejor["total_amount"])
        esc_ida, esc_vuelta = escalas_de_oferta(mejor)

        log.info(f"  Mejor: USD {precio:.0f} ({mejor['owner']['name']})")

        # ── Guardar en DB ──
        guardar_precio(nombre, precio, mejor["owner"]["name"], esc_ida, esc_vuelta)

        # ── Evaluar condiciones ──
        minimo_hist = obtener_minimo_historico(nombre)
        baratas = sorted(
            [o for o in ofertas if float(o["total_amount"]) <= PRECIO_MAXIMO],
            key=lambda x: float(x["total_amount"])
        )

        if baratas:
            alertas_umbral.append((nombre, baratas, generar_links(busqueda), busqueda))

        # Nuevo mínimo histórico (la DB ya tiene el actual guardado,
        # comparamos contra el registro anterior)
        previos = obtener_ultimos_precios(nombre, 50)
        if len(previos) > 1:
            min_previo = min(previos[1:])  # ignora el que acabamos de guardar
            if precio < min_previo:
                caida = calcular_caida_porcentual(nombre, precio)
                alertas_minimo.append((nombre, precio, min_previo, caida))
                log.info(f"  ★ Nuevo mínimo histórico: USD {precio:.0f} (antes {min_previo:.0f})")

        if detectar_tendencia_bajista(nombre, precio):
            log.info(f"  📉 Tendencia bajista detectada ({BAJAS_CONSECUTIVAS} bajas consecutivas)")
            alertas_tendencia.append((nombre, precio, generar_links(busqueda), busqueda))

    # ── Construir mensaje ──────────────────────────────────────────

    if not (alertas_umbral or alertas_tendencia or alertas_minimo):
        log.info("Sin alertas que enviar.")
        log.info("=== Fin ===\n")
        return

    partes = [f"✈️ <b>FLIGHT MONITOR</b> — {ahora}\n"]

    # Ofertas bajo umbral
    if alertas_umbral:
        total = sum(len(b) for _, b, _, _ in alertas_umbral)
        partes.append(f"🚨 <b>{total} oferta(s) bajo USD {PRECIO_MAXIMO}</b>\n")
        for nombre, baratas, links, busqueda in alertas_umbral:
            skyscanner, google, kayak = links
            partes.append(f"<b>{nombre}</b>")
            partes.append(f"  {busqueda['ida_fecha']} → {busqueda['vuelta_fecha']}")
            for oferta in baratas[:3]:
                partes.append(formatear_oferta(oferta))
            partes.append(obtener_resumen_tendencia(nombre))
            partes.append(
                f'🔍 <a href="{skyscanner}">Skyscanner</a>'
                f' | <a href="{google}">Google</a>'
                f' | <a href="{kayak}">Kayak</a>\n'
            )

    # Nuevos mínimos históricos
    if alertas_minimo:
        partes.append("⭐ <b>Nuevos mínimos históricos</b>")
        for nombre, precio, anterior, caida in alertas_minimo:
            linea = f"  {nombre}: USD {precio:.0f}"
            if caida:
                linea += f" (↓{caida:.1f}% vs máx reciente)"
            partes.append(linea)
        partes.append("")

    # Tendencia bajista
    if alertas_tendencia:
        partes.append(f"📉 <b>Tendencia bajista ({BAJAS_CONSECUTIVAS} bajas seguidas)</b>")
        for nombre, precio, links, busqueda in alertas_tendencia:
            skyscanner, google, kayak = links
            partes.append(
                f"  {nombre}: USD {precio:.0f} — "
                f'<a href="{skyscanner}">ver vuelos</a>'
            )
            partes.append(obtener_resumen_tendencia(nombre))
        partes.append("")

    enviar_telegram("\n".join(partes))
    log.info("Alerta enviada.")
    log.info("=== Fin ===\n")


if __name__ == "__main__":
    main()
