import time
import traceback
from datetime import datetime
from flight_monitor import main

INTERVALO_HORAS = 6

if __name__ == "__main__":
    print(f"Worker iniciado - ejecuta cada {INTERVALO_HORAS} horas")
    print(f"Hora de inicio: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    while True:
        try:
            print(f"\n--- Ejecutando monitor: {datetime.now().strftime('%Y-%m-%d %H:%M')} ---")
            main()
        except Exception as e:
            print(f"Error en ejecucion: {e}")
            traceback.print_exc()

        proxima = INTERVALO_HORAS * 3600
        print(f"Proxima ejecucion en {INTERVALO_HORAS} horas...")
        time.sleep(proxima)
