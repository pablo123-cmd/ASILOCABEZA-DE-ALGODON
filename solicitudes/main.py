from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

# ==================================================
# CREACIÓN DE LA APLICACIÓN
# ==================================================

app = FastAPI(
    title="Microservicio de Solicitudes Médicas",
    description="Microservicio para gestionar solicitudes médicas del asilo",
    version="1.0"
)


# ==================================================
# LISTA DE SOLICITUDES
# ==================================================

solicitudes = [
    {
        "id": 1,
        "paciente_id": 1,
        "especialidad": "Cardiología",
        "motivo": "Dolor en el pecho",
        "estado": "Pendiente"
    },
    {
        "id": 2,
        "paciente_id": 2,
        "especialidad": "Medicina Interna",
        "motivo": "Control médico",
        "estado": "Asignada"
    }
]


# ==================================================
# PÁGINA PRINCIPAL
# ==================================================

@app.get("/", response_class=HTMLResponse)
def inicio():

    tarjetas = ""

    for solicitud in solicitudes:

        tarjetas += f"""
        <div class="tarjeta">

            <h3>
                Solicitud #{solicitud["id"]}
            </h3>

            <p>
                <strong>Paciente:</strong>
                {solicitud["paciente_id"]}
            </p>

            <p>
                <strong>Especialidad:</strong>
                {solicitud["especialidad"]}
            </p>

            <p>
                <strong>Motivo:</strong>
                {solicitud["motivo"]}
            </p>

            <p>
                <strong>Estado:</strong>
                {solicitud["estado"]}
            </p>

        </div>
        """

    return f"""
    <!DOCTYPE html>

    <html lang="es">

    <head>

        <meta charset="UTF-8">

        <meta name="viewport"
              content="width=device-width, initial-scale=1.0">

        <title>Solicitudes Médicas</title>

        <style>

            * {{
                box-sizing: border-box;
            }}

            body {{
                margin: 0;
                font-family: Arial, sans-serif;
                background-color: #f2f4f7;
            }}

            .encabezado {{
                background-color: #2e7d32;
                color: white;
                text-align: center;
                padding: 25px;
            }}

            .encabezado h1 {{
                margin: 0;
            }}

            .contenedor {{
                max-width: 900px;
                margin: 30px auto;
                padding: 20px;
            }}

            .formulario {{
                background-color: white;
                padding: 25px;
                border-radius: 10px;

                box-shadow:
                    0 3px 10px rgba(0,0,0,0.12);
            }}

            .formulario h2 {{
                margin-top: 0;
                color: #333;
            }}

            label {{
                display: block;
                margin-top: 15px;
                margin-bottom: 5px;
                font-weight: bold;
            }}

            input,
            select {{
                width: 100%;
                padding: 12px;

                border: 1px solid #ccc;
                border-radius: 5px;

                font-size: 15px;
            }}

            button {{
                width: 100%;
                margin-top: 25px;
                padding: 13px;

                border: none;
                border-radius: 5px;

                background-color: #2e7d32;
                color: white;

                font-size: 16px;
                cursor: pointer;
            }}

            button:hover {{
                background-color: #1b5e20;
            }}

            .lista {{
                margin-top: 30px;
            }}

            .lista h2 {{
                color: #333;
            }}

            .tarjeta {{
                background-color: white;
                padding: 20px;
                margin-bottom: 15px;

                border-left: 5px solid #2e7d32;
                border-radius: 7px;

                box-shadow:
                    0 2px 8px rgba(0,0,0,0.10);
            }}

            .tarjeta h3 {{
                margin-top: 0;
                color: #2e7d32;
            }}

            .tarjeta p {{
                margin: 8px 0;
                color: #444;
            }}

            .volver {{
                display: block;
                text-align: center;
                margin-top: 25px;

                color: #2e7d32;
                text-decoration: none;

                font-weight: bold;
            }}

        </style>

    </head>


    <body>


        <div class="encabezado">

            <h1>
                📋 Solicitudes Médicas
            </h1>

            <p>
                Asilo Cabeza de Algodón
            </p>

        </div>


        <div class="contenedor">


            <!-- FORMULARIO -->

            <div class="formulario">

                <h2>
                    Nueva Solicitud Médica
                </h2>


                <form
                    action="/crear"
                    method="post"
                >


                    <label>
                        ID del paciente
                    </label>

                    <input
                        type="number"
                        name="paciente_id"
                        placeholder="Ejemplo: 1"
                        min="1"
                        required
                    >


                    <label>
                        Especialidad
                    </label>

                    <select
                        name="especialidad"
                        required
                    >

                        <option value="">
                            Seleccione una especialidad
                        </option>

                        <option value="Cardiología">
                            Cardiología
                        </option>

                        <option value="Medicina Interna">
                            Medicina Interna
                        </option>

                        <option value="Geriatría">
                            Geriatría
                        </option>

                        <option value="Neurología">
                            Neurología
                        </option>

                        <option value="Traumatología">
                            Traumatología
                        </option>

                    </select>


                    <label>
                        Motivo de la solicitud
                    </label>

                    <input
                        type="text"
                        name="motivo"
                        placeholder="Ingrese el motivo"
                        required
                    >


                    <button type="submit">

                        Registrar solicitud

                    </button>


                </form>

            </div>


            <!-- LISTA -->

            <div class="lista">

                <h2>
                    Solicitudes registradas
                </h2>

                {tarjetas}

            </div>


            <a
                class="volver"
                href="http://127.0.0.1:8002"
            >
                ← Volver al menú principal
            </a>


        </div>


    </body>

    </html>
    """


# ==================================================
# CREAR SOLICITUD DESDE EL FORMULARIO
# ==================================================

@app.post("/crear", response_class=HTMLResponse)
def crear_desde_formulario(
    paciente_id: int = Form(...),
    especialidad: str = Form(...),
    motivo: str = Form(...)
):

    nueva_solicitud = {

        "id": len(solicitudes) + 1,

        "paciente_id": paciente_id,

        "especialidad": especialidad,

        "motivo": motivo,

        "estado": "Pendiente"
    }

    solicitudes.append(nueva_solicitud)


    return f"""
    <!DOCTYPE html>

    <html lang="es">

    <head>

        <meta charset="UTF-8">

        <title>Solicitud creada</title>

        <style>

            body {{
                font-family: Arial, sans-serif;
                background-color: #f2f4f7;
                padding: 40px;
            }}

            .mensaje {{
                max-width: 600px;
                margin: auto;

                background-color: white;

                padding: 30px;

                border-radius: 10px;

                text-align: center;

                box-shadow:
                    0 3px 10px rgba(0,0,0,0.12);
            }}

            .exito {{
                color: #2e7d32;

                font-size: 22px;

                font-weight: bold;

                margin-bottom: 20px;
            }}

            .datos {{
                background-color: #f5f5f5;

                padding: 20px;

                border-radius: 5px;

                text-align: left;
            }}

            a {{
                display: block;

                margin-top: 20px;

                padding: 12px;

                background-color: #2e7d32;

                color: white;

                text-decoration: none;

                border-radius: 5px;
            }}

        </style>

    </head>


    <body>

        <div class="mensaje">


            <div class="exito">

                ✓ Solicitud creada correctamente

            </div>


            <div class="datos">

                <p>
                    <strong>ID:</strong>
                    {nueva_solicitud["id"]}
                </p>

                <p>
                    <strong>Paciente:</strong>
                    {paciente_id}
                </p>

                <p>
                    <strong>Especialidad:</strong>
                    {especialidad}
                </p>

                <p>
                    <strong>Motivo:</strong>
                    {motivo}
                </p>

                <p>
                    <strong>Estado:</strong>
                    Pendiente
                </p>

            </div>


            <a href="/">

                Ver solicitudes

            </a>


            <a href="http://127.0.0.1:8002">

                Volver al menú principal

            </a>


        </div>

    </body>

    </html>
    """


# ==================================================
# GET - OBTENER TODAS LAS SOLICITUDES
# ==================================================

@app.get("/solicitudes")
def obtener_solicitudes():

    return solicitudes


# ==================================================
# GET - OBTENER UNA SOLICITUD
# ==================================================

@app.get("/solicitudes/{solicitud_id}")
def obtener_solicitud(solicitud_id: int):

    for solicitud in solicitudes:

        if solicitud["id"] == solicitud_id:

            return solicitud

    return {
        "mensaje": "Solicitud no encontrada"
    }


# ==================================================
# POST - CREAR SOLICITUD
# ==================================================

@app.post("/solicitudes")
def crear_solicitud(solicitud: dict):

    solicitud["id"] = len(solicitudes) + 1

    solicitud["estado"] = "Pendiente"

    solicitudes.append(solicitud)

    return {
        "mensaje": "Solicitud creada correctamente",
        "solicitud": solicitud
    }


# ==================================================
# PUT - ACTUALIZAR SOLICITUD
# ==================================================

@app.put("/solicitudes/{solicitud_id}")
def actualizar_solicitud(
    solicitud_id: int,
    datos: dict
):

    for solicitud in solicitudes:

        if solicitud["id"] == solicitud_id:

            solicitud["especialidad"] = datos.get(
                "especialidad",
                solicitud["especialidad"]
            )

            solicitud["motivo"] = datos.get(
                "motivo",
                solicitud["motivo"]
            )

            solicitud["estado"] = datos.get(
                "estado",
                solicitud["estado"]
            )

            return {
                "mensaje": "Solicitud actualizada correctamente",
                "solicitud": solicitud
            }

    return {
        "mensaje": "Solicitud no encontrada"
    }


# ==================================================
# DELETE - ELIMINAR SOLICITUD
# ==================================================

@app.delete("/solicitudes/{solicitud_id}")
def eliminar_solicitud(solicitud_id: int):

    for solicitud in solicitudes:

        if solicitud["id"] == solicitud_id:

            solicitudes.remove(solicitud)

            return {
                "mensaje": "Solicitud eliminada correctamente"
            }

    return {
        "mensaje": "Solicitud no encontrada"
    }