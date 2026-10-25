"""
Inicia todos los servicios del sistema con un solo comando:

    python iniciar.py            (datos en MySQL)
    python iniciar.py --memoria  (sin MySQL; los datos se pierden al cerrar)

Presione Ctrl+C para detenerlos.
"""

import os
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


def verificar_mysql():
    """Comprueba la conexión antes de iniciar, con un mensaje claro si falla."""

    from comun import config
    from comun.repositorio import BaseDeDatosNoDisponible, RepositorioMySQL

    try:
        RepositorioMySQL("configuracion").obtener(1)
    except BaseDeDatosNoDisponible as error:
        print(f"No se pudo conectar a MySQL en {config.MYSQL_HOST}:{config.MYSQL_PUERTO} "
              f"(base de datos {config.MYSQL_BD}).")
        print(f"Detalle: {error}")
        print("Verifique que MySQL esté encendido y que se ejecutó docs/bd/asilo.sql,")
        print("o use  python iniciar.py --memoria  para probar sin base de datos.")
        sys.exit(1)

    print(f"Conectado a MySQL ({config.MYSQL_BD}).")


def main():
    if "--memoria" in sys.argv:
        os.environ["ASILO_BD"] = "memoria"
        print("Modo memoria: los datos se pierden al detener el sistema.")
    else:
        os.environ.setdefault("ASILO_BD", "mysql")
        if os.environ["ASILO_BD"] == "mysql":
            verificar_mysql()

    # En la nube (Render) la variable PORT indica dónde debe escuchar el
    # menú principal; los demás servicios quedan solo dentro del servidor.
    puerto_publico = os.getenv("PORT")
    procesos = []

    for nombre, aplicacion, puerto in SERVICIOS:
        host = "127.0.0.1"
        if puerto_publico and aplicacion.startswith("gateway"):
            host, puerto = "0.0.0.0", int(puerto_publico)

        print(f"Iniciando {nombre} en http://{host}:{puerto}")
        procesos.append(subprocess.Popen(
            [sys.executable, "-m", "uvicorn", aplicacion,
             "--host", host, "--port", str(puerto)],
            cwd=CARPETA
        ))

    if not puerto_publico:
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
