"""
Inicia todos los servicios del sistema con un solo comando:

    python iniciar.py

Presione Ctrl+C para detenerlos.
"""

import subprocess
import sys
import time
from pathlib import Path

SERVICIOS = [
    ("Pacientes", "pacientes.main:app", 8000),
    ("Solicitudes médicas", "solicitudes.main:app", 8001),
    ("Menú principal (gateway)", "gateway.main:app", 8002),
    ("Atención médica", "medico.main:app", 8003),
    ("Finanzas", "finanzas.main:app", 8004),
]

CARPETA = Path(__file__).parent


def main():
    procesos = []

    for nombre, aplicacion, puerto in SERVICIOS:
        print(f"Iniciando {nombre} en http://127.0.0.1:{puerto}")
        procesos.append(subprocess.Popen(
            [sys.executable, "-m", "uvicorn", aplicacion,
             "--host", "127.0.0.1", "--port", str(puerto)],
            cwd=CARPETA
        ))

    print("\nAbra el sistema en: http://127.0.0.1:8002")
    print("Presione Ctrl+C para detener todos los servicios.\n")

    try:
        while all(p.poll() is None for p in procesos):
            time.sleep(1)
        print("Un servicio se detuvo; revise los mensajes de arriba.")
    except KeyboardInterrupt:
        pass
    finally:
        for proceso in procesos:
            proceso.terminate()
        for proceso in procesos:
            proceso.wait()
        print("Servicios detenidos.")


if __name__ == "__main__":
    main()
