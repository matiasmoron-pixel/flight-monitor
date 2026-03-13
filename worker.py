import os
import time
import traceback
import requests
from datetime import datetime

DUFFEL_TOKEN = os.getenv("DUFFEL_TOKEN")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

PRECIO_MAXIMO = 1500
INTERVALO_HORAS = 6

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

    skyscanner = (
        f"https://www.skyscanner.com.ar/transport/flights/buea/mnl/"
        f"{ida_yymmdd}/{vuelta_yymmdd}/?adults=1"
    )

    google = (
        f"https://www.google.com/travel/flights?q=Flights+to+{destino}+from+"
        f"{origen}+on+{ida}+through+{vuelta}&curr=USD"
    )

    kayak = (
        f"https://www.kayak.com/flights/{origen}-{destino}/{ida}/{vuelta}"
        f"?sort=bestflight_a&fs=stops=0"
    )

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


def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
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
    tramos_texto = "\n".join(tramos)
    return f"USD {price} - {airline}\n{tramos_texto}"


def ejecutar_monitor():
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"=== Flight Monitor - {ahora} ===\n")

    alertas_por_busqueda = []

    for busqueda in BUSQUEDAS:
        nombre = busqueda["nombre"]
        print(f"Buscando: {nombre}...")
        print(f"  Ida: {busqueda['ida_fecha']} / Vuelta: {busqueda['vuelta_fecha']}")

        ofertas = buscar_vuelos(busqueda)
        print(f"  Encontradas: {len(ofertas)} ofertas")

        baratas = sorted(
            [o for o in ofertas if float(o["total_amount"]) <= PRECIO_MAXIMO],
            key=lambda x: float(x["total_amount"])
        )
        print(f"  Por debajo de USD {PRECIO_MAXIMO}: {len(baratas)}")

        if baratas:
            links = generar_links(busqueda)
            alertas_por_busqueda.append((nombre, baratas, links))

        if ofertas:
            mejor = min(ofertas, key=lambda x: float(x["total_amount"]))
            print(f"  Mejor precio: USD {mejor['total_amount']} ({mejor['owner']['name']})")

        print()

    if alertas_por_busqueda:
        total = sum(len(baratas) for _, baratas, _ in alertas_por_busqueda)
        mensaje = f"<b>ALERTA DE VUELOS</b>\n"
        mensaje += f"Encontre {total} oferta(s) por debajo de USD {PRECIO_MAXIMO}:\n\n"

        for nombre, baratas, links in alertas_por_busqueda:
            skyscanner, google, kayak = links
            mensaje += f"<b>{nombre}</b>\n"
            for oferta in baratas:
                mensaje += formatear_oferta(oferta) + "\n"
            mensaje += f"\nBuscar y reservar:\n"
            mensaje += f"<a href='{skyscanner}'>Skyscanner</a>"
            mensaje += f" | <a href='{google}'>Google Flights</a>"
            mensaje += f" | <a href='{kayak}'>Kayak</a>\n\n"

        mensaje += f"Buscado: {ahora}"

        enviar_telegram(mensaje)
        print("ALERTA ENVIADA A TELEGRAM")
    else:
        print(f"No se encontraron vuelos por debajo de USD {PRECIO_MAXIMO}.")
        print("No se envia alerta.")

    print("\n=== Fin ===")


if __name__ == "__main__":
    print(f"Worker iniciado - ejecuta cada {INTERVALO_HORAS} horas")
    print(f"Hora de inicio: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    while True:
        try:
            print(f"\n--- Ejecutando monitor: {datetime.now().strftime('%Y-%m-%d %H:%M')} ---")
            ejecutar_monitor()
        except Exception as e:
            print(f"Error en ejecucion: {e}")
            traceback.print_exc()

        proxima = INTERVALO_HORAS * 3600
        print(f"Proxima ejecucion en {INTERVALO_HORAS} horas...")
        time.sleep(proxima)
