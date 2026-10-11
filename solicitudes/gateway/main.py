from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import httpx

app = FastAPI(
    title="Sistema Asilo Cabeza de Algodón",
    description="Gateway principal del sistema",
    version="1.0"
)


# ==================================================
# CONFIGURACIÓN DE LOS MICROSERVICIOS
# ==================================================

PACIENTES_URL = "http://127.0.0.1:8000"
SOLICITUDES_URL = "http://127.0.0.1:8001"


# ==================================================
# PÁGINA PRINCIPAL
# ==================================================

@app.get("/", response_class=HTMLResponse)
def inicio():

    return """
    <!DOCTYPE html>

    <html lang="es">

    <head>

        <meta charset="UTF-8">

        <meta name="viewport"
              content="width=device-width, initial-scale=1.0">

        <title>Asilo Cabeza de Algodón</title>

        <style>

            * {
                box-sizing: border-box;
            }

            body {
                margin: 0;
                font-family: Arial, sans-serif;
                background-color: #f2f4f7;
            }

            .encabezado {
                background-color: #2e7d32;
                color: white;
                padding: 30px;
                text-align: center;
            }

            .encabezado h1 {
                margin: 0;
                font-size: 32px;
            }

            .encabezado p {
                margin-top: 10px;
                font-size: 17px;
            }

            .contenedor {
                max-width: 1000px;
                margin: 40px auto;
                padding: 20px;
            }

            .titulo {
                text-align: center;
                color: #333;
                margin-bottom: 30px;
            }

            .modulos {
                display: grid;
                grid-template-columns:
                    repeat(auto-fit, minmax(220px, 1fr));

                gap: 25px;
            }

            .modulo {
                background-color: white;
                padding: 30px;
                border-radius: 10px;
                text-align: center;

                box-shadow:
                    0 3px 10px rgba(0,0,0,0.12);
            }

            .icono {
                font-size: 50px;
                margin-bottom: 15px;
            }

            .modulo h2 {
                color: #333;
                margin-bottom: 10px;
            }

            .modulo p {
                color: #666;
                min-height: 45px;
            }

            .boton {
                display: inline-block;
                width: 100%;
                padding: 12px;
                margin-top: 15px;

                background-color: #2e7d32;
                color: white;

                text-decoration: none;

                border-radius: 5px;

                font-weight: bold;
            }

            .boton:hover {
                background-color: #1b5e20;
            }

            .estado {
                margin-top: 40px;
                padding: 20px;

                background-color: white;

                border-radius: 10px;

                text-align: center;
            }

            .pie {
                text-align: center;
                color: #777;
                padding: 30px;
            }

        </style>

    </head>

    <body>

        <div class="encabezado">

            <h1>
                Asilo Cabeza de Algodón
            </h1>

            <p>
                Sistema de Administración
            </p>

        </div>


        <div class="contenedor">

            <h2 class="titulo">
                Módulos del Sistema
            </h2>


            <div class="modulos">


                <!-- PACIENTES -->

                <div class="modulo">

                    <div class="icono">
                        👴
                    </div>

                    <h2>
                        Registro de Ancianos
                    </h2>

                    <p>
                        Registrar y consultar información
                        de los pacientes.
                    </p>

                    <a
                        class="boton"
                        href="/pacientes"
                    >
                        Entrar
                    </a>

                </div>


                <!-- SOLICITUDES -->

                <div class="modulo">

                    <div class="icono">
                        📋
                    </div>

                    <h2>
                        Solicitudes
                    </h2>

                    <p>
                        Administrar las solicitudes
                        del sistema.
                    </p>

                    <a
                        class="boton"
                        href="/solicitudes"
                    >
                        Entrar
                    </a>

                </div>


                <!-- FACTURACIÓN -->

                <div class="modulo">

                    <div class="icono">
                        💰
                    </div>

                    <h2>
                        Facturación
                    </h2>

                    <p>
                        Módulo preparado para
                        facturación y ventas.
                    </p>

                    <a
                        class="boton"
                        href="/facturacion"
                    >
                        Entrar
                    </a>

                </div>


                <!-- REPORTES -->

                <div class="modulo">

                    <div class="icono">
                        📊
                    </div>

                    <h2>
                        Reportes
                    </h2>

                    <p>
                        Consultar información
                        general del sistema.
                    </p>

                    <a
                        class="boton"
                        href="/reportes"
                    >
                        Entrar
                    </a>

                </div>

            </div>


            <div class="estado">

                <strong>
                    Sistema principal funcionando
                </strong>

                <p>
                    Desde este menú se puede acceder
                    a los diferentes módulos.
                </p>

            </div>

        </div>


        <div class="pie">

            Asilo Cabeza de Algodón © 2026

        </div>

    </body>

    </html>
    """


# ==================================================
# MÓDULO DE PACIENTES
# ==================================================

@app.get("/pacientes", response_class=HTMLResponse)
async def modulo_pacientes():

    return """
    <!DOCTYPE html>

    <html lang="es">

    <head>

        <meta charset="UTF-8">

        <title>Registro de Ancianos</title>

        <style>

            body {
                font-family: Arial, sans-serif;
                background-color: #f2f4f7;
                padding: 40px;
            }

            .contenedor {
                max-width: 600px;
                margin: auto;
                background-color: white;
                padding: 30px;
                border-radius: 10px;

                box-shadow:
                    0 3px 10px rgba(0,0,0,0.12);
            }

            h1 {
                text-align: center;
                color: #333;
            }

            label {
                display: block;
                margin-top: 15px;
                margin-bottom: 5px;
                font-weight: bold;
            }

            input {
                width: 100%;
                padding: 12px;
                border: 1px solid #ccc;
                border-radius: 5px;
            }

            button {
                width: 100%;
                margin-top: 25px;
                padding: 12px;

                border: none;
                border-radius: 5px;

                background-color: #2e7d32;
                color: white;

                font-size: 16px;
                cursor: pointer;
            }

            button:hover {
                background-color: #1b5e20;
            }

            .volver {
                display: block;
                text-align: center;
                margin-top: 20px;
                color: #2e7d32;
                text-decoration: none;
            }

        </style>

    </head>

    <body>

        <div class="contenedor">

            <h1>
                Registro de Ancianos
            </h1>

            <form
                action="/pacientes/registrar"
                method="post"
            >

                <label>
                    Nombre completo
                </label>

                <input
                    type="text"
                    name="nombre"
                    placeholder="Ingrese el nombre"
                    required
                >


                <label>
                    Edad
                </label>

                <input
                    type="number"
                    name="edad"
                    placeholder="Ingrese la edad"
                    required
                >


                <label>
                    Habitación
                </label>

                <input
                    type="text"
                    name="habitacion"
                    placeholder="Ejemplo: A-03"
                    required
                >


                <button type="submit">

                    Registrar paciente

                </button>

            </form>


            <a
                class="volver"
                href="/"
            >
                ← Volver al menú principal
            </a>

        </div>

    </body>

    </html>
    """


# ==================================================
# REGISTRAR PACIENTE DESDE EL GATEWAY
# ==================================================

from fastapi import Form


@app.post("/pacientes/registrar", response_class=HTMLResponse)
async def registrar_paciente(
    nombre: str = Form(...),
    edad: int = Form(...),
    habitacion: str = Form(...)
):

    datos = {
        "nombre": nombre,
        "edad": edad,
        "habitacion": habitacion
    }

    try:

        async with httpx.AsyncClient() as cliente:

            respuesta = await cliente.post(
                f"{PACIENTES_URL}/pacientes",
                json=datos
            )

        if respuesta.status_code == 200:

            return f"""
            <html>

            <head>

                <title>Paciente registrado</title>

                <style>

                    body {{
                        font-family: Arial;
                        background-color: #f2f4f7;
                        padding: 40px;
                    }}

                    .mensaje {{
                        max-width: 500px;
                        margin: auto;
                        background: white;
                        padding: 30px;
                        border-radius: 10px;
                        text-align: center;
                    }}

                    .exito {{
                        color: #2e7d32;
                        font-size: 22px;
                        font-weight: bold;
                    }}

                    a {{
                        display: block;
                        margin-top: 25px;
                        background-color: #2e7d32;
                        color: white;
                        padding: 12px;
                        text-decoration: none;
                        border-radius: 5px;
                    }}

                </style>

            </head>

            <body>

                <div class="mensaje">

                    <div class="exito">
                        ✓ Paciente registrado correctamente
                    </div>

                    <p>
                        Nombre: {nombre}
                    </p>

                    <p>
                        Edad: {edad}
                    </p>

                    <p>
                        Habitación: {habitacion}
                    </p>

                    <a href="/pacientes">
                        Registrar otro paciente
                    </a>

                    <a href="/">
                        Volver al menú principal
                    </a>

                </div>

            </body>

            </html>
            """

        else:

            return """
            <h1>
                Error al registrar el paciente
            </h1>

            <a href="/pacientes">
                Volver
            </a>
            """

    except Exception as error:

        return f"""
        <h1>
            No se pudo conectar con el
            microservicio de pacientes.
        </h1>

        <p>
            {error}
        </p>

        <a href="/">
            Volver al menú
        </a>
        """


# ==================================================
# MÓDULO DE SOLICITUDES
# ==================================================

@app.get("/solicitudes", response_class=HTMLResponse)
async def modulo_solicitudes():

    try:

        async with httpx.AsyncClient() as cliente:

            respuesta = await cliente.get(
                f"{SOLICITUDES_URL}/"
            )

        datos = respuesta.text

    except:

        datos = "Microservicio de solicitudes no disponible."

    return f"""
    <!DOCTYPE html>

    <html lang="es">

    <head>

        <meta charset="UTF-8">

        <title>Solicitudes</title>

        <style>

            body {{
                font-family: Arial;
                background-color: #f2f4f7;
                padding: 40px;
            }}

            .contenedor {{
                max-width: 700px;
                margin: auto;
                background: white;
                padding: 30px;
                border-radius: 10px;
            }}

            h1 {{
                color: #333;
            }}

            .respuesta {{
                background-color: #f5f5f5;
                padding: 20px;
                margin-top: 20px;
                border-radius: 5px;
            }}

            a {{
                display: block;
                margin-top: 20px;
                color: #2e7d32;
            }}

        </style>

    </head>

    <body>

        <div class="contenedor">

            <h1>
                📋 Módulo de Solicitudes
            </h1>

            <p>
                Este módulo se comunica con el
                microservicio de solicitudes.
            </p>

            <div class="respuesta">

                <strong>
                    Respuesta del microservicio:
                </strong>

                <p>
                    {datos}
                </p>

            </div>

            <a href="/">
                ← Volver al menú principal
            </a>

        </div>

    </body>

    </html>
    """


# ==================================================
# FACTURACIÓN
# ==================================================

@app.get("/facturacion", response_class=HTMLResponse)
def facturacion():

    return """
    <!DOCTYPE html>

    <html lang="es">

    <head>

        <meta charset="UTF-8">

        <title>Facturación</title>

        <style>

            body {
                font-family: Arial;
                background-color: #f2f4f7;
                padding: 40px;
            }

            .contenedor {
                max-width: 600px;
                margin: auto;
                background: white;
                padding: 30px;
                border-radius: 10px;
                text-align: center;
            }

            h1 {
                color: #333;
            }

            .mensaje {
                padding: 20px;
                background-color: #f5f5f5;
                border-radius: 5px;
                margin-top: 20px;
            }

            a {
                display: block;
                margin-top: 20px;
                color: #2e7d32;
            }

        </style>

    </head>

    <body>

        <div class="contenedor">

            <h1>
                💰 Facturación
            </h1>

            <div class="mensaje">

                <p>
                    Módulo de facturación en desarrollo.
                </p>

                <p>
                    Próximamente se podrán crear
                    y consultar facturas.
                </p>

            </div>

            <a href="/">
                ← Volver al menú principal
            </a>

        </div>

    </body>

    </html>
    """


# ==================================================
# REPORTES
# ==================================================

@app.get("/reportes", response_class=HTMLResponse)
def reportes():

    return """
    <!DOCTYPE html>

    <html lang="es">

    <head>

        <meta charset="UTF-8">

        <title>Reportes</title>

        <style>

            body {
                font-family: Arial;
                background-color: #f2f4f7;
                padding: 40px;
            }

            .contenedor {
                max-width: 600px;
                margin: auto;
                background: white;
                padding: 30px;
                border-radius: 10px;
                text-align: center;
            }

            .reporte {
                background-color: #f5f5f5;
                padding: 20px;
                margin-top: 15px;
                border-radius: 5px;
            }

            a {
                display: block;
                margin-top: 25px;
                color: #2e7d32;
            }

        </style>

    </head>

    <body>

        <div class="contenedor">

            <h1>
                📊 Reportes
            </h1>

            <div class="reporte">

                <strong>
                    Reportes del sistema
                </strong>

                <p>
                    Este módulo permitirá consultar
                    información general del asilo.
                </p>

            </div>

            <a href="/">
                ← Volver al menú principal
            </a>

        </div>

    </body>

    </html>
    """