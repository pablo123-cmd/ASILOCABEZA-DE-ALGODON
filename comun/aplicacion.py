from fastapi import FastAPI

from comun.errores import configurar_errores


def crear_servicio(titulo, descripcion, nombre):
    """Crea la aplicación FastAPI de un microservicio."""

    app = FastAPI(title=titulo, description=descripcion, version="2.0")
    configurar_errores(app)

    @app.get("/", tags=["Servicio"])
    def estado():
        return {
            "servicio": nombre,
            "estado": "funcionando",
            "documentacion": "/docs"
        }

    return app
