from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

# --------------------------------------------------
# CREACIÓN DE LA APLICACIÓN
# --------------------------------------------------

app = FastAPI(
    title="Microservicio de Pacientes",
    description="Microservicio para administrar pacientes del asilo",
    version="1.0"
)

# --------------------------------------------------
# LISTA DE PACIENTES
# --------------------------------------------------

pacientes = [
    {
        "id": 1,
        "nombre": "Juan Pérez",
        "edad": 75,
        "habitacion": "A-01"
    },
    {
        "id": 2,
        "nombre": "María López",
        "edad": 80,
        "habitacion": "A-02"
    }
]

# --------------------------------------------------
# PÁGINA PRINCIPAL
# --------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def inicio():

    return """
    <!DOCTYPE html>
    <html lang="es">

    <head>

        <meta charset="UTF-8">

        <meta name="viewport"
              content="width=device-width, initial-scale=1.0">

        <title>Registro de Ancianos</title>

        <style>

            body {
                font-family: Arial, sans-serif;
                background-color: #f2f4f7;
                margin: 0;
                padding: 40px;
            }

            .contenedor {
                max-width: 500px;
                margin: auto;
                background-color: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.15);
            }

            h1 {
                text-align: center;
                color: #333;
                margin-bottom: 10px;
            }

            .subtitulo {
                text-align: center;
                color: #666;
                margin-bottom: 30px;
            }

            label {
                display: block;
                margin-top: 15px;
                margin-bottom: 6px;
                font-weight: bold;
                color: #333;
            }

            input {
                width: 100%;
                padding: 12px;
                box-sizing: border-box;
                border: 1px solid #ccc;
                border-radius: 5px;
                font-size: 15px;
            }

            input:focus {
                outline: none;
                border-color: #2e7d32;
            }

            button {
                width: 100%;
                margin-top: 25px;
                padding: 13px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
                background-color: #2e7d32;
                color: white;
            }

            button:hover {
                background-color: #1b5e20;
            }

        </style>

    </head>

    <body>

        <div class="contenedor">

            <h1>Registro de Ancianos</h1>

            <p class="subtitulo">
                Ingrese los datos del paciente
            </p>

            <form action="/registrar" method="post">

                <label for="nombre">
                    Nombre completo
                </label>

                <input
                    type="text"
                    id="nombre"
                    name="nombre"
                    placeholder="Ingrese el nombre completo"
                    required
                >

                <label for="edad">
                    Edad
                </label>

                <input
                    type="number"
                    id="edad"
                    name="edad"
                    placeholder="Ingrese la edad"
                    min="1"
                    required
                >

                <label for="habitacion">
                    Habitación
                </label>

                <input
                    type="text"
                    id="habitacion"
                    name="habitacion"
                    placeholder="Ejemplo: A-03"
                    required
                >

                <button type="submit">
                    Registrar paciente
                </button>

            </form>

        </div>

    </body>

    </html>
    """


# --------------------------------------------------
# REGISTRAR PACIENTE DESDE EL FORMULARIO
# --------------------------------------------------

@app.post("/registrar", response_class=HTMLResponse)
def registrar_paciente(
    nombre: str = Form(...),
    edad: int = Form(...),
    habitacion: str = Form(...)
):

    nuevo_paciente = {
        "id": len(pacientes) + 1,
        "nombre": nombre,
        "edad": edad,
        "habitacion": habitacion
    }

    pacientes.append(nuevo_paciente)

    return f"""
    <!DOCTYPE html>

    <html lang="es">

    <head>

        <meta charset="UTF-8">

        <meta name="viewport"
              content="width=device-width, initial-scale=1.0">

        <title>Paciente registrado</title>

        <style>

            body {{
                font-family: Arial, sans-serif;
                background-color: #f2f4f7;
                margin: 0;
                padding: 40px;
            }}

            .mensaje {{
                max-width: 500px;
                margin: auto;
                background-color: white;
                padding: 30px;
                border-radius: 10px;
                text-align: center;
                box-shadow: 0 2px 10px rgba(0,0,0,0.15);
            }}

            .exito {{
                color: #2e7d32;
                font-size: 22px;
                font-weight: bold;
                margin-bottom: 25px;
            }}

            .datos {{
                text-align: left;
                background-color: #f5f5f5;
                padding: 15px;
                border-radius: 5px;
            }}

            .datos p {{
                margin: 10px 0;
            }}

            a {{
                display: block;
                margin-top: 25px;
                text-decoration: none;
                background-color: #2e7d32;
                color: white;
                padding: 12px;
                border-radius: 5px;
            }}

            a:hover {{
                background-color: #1b5e20;
            }}

        </style>

    </head>

    <body>

        <div class="mensaje">

            <div class="exito">
                ✓ Paciente registrado correctamente
            </div>

            <div class="datos">

                <p>
                    <strong>Nombre:</strong>
                    {nombre}
                </p>

                <p>
                    <strong>Edad:</strong>
                    {edad} años
                </p>

                <p>
                    <strong>Habitación:</strong>
                    {habitacion}
                </p>

            </div>

            <a href="/">
                Registrar otro paciente
            </a>

        </div>

    </body>

    </html>
    """


# --------------------------------------------------
# GET - OBTENER TODOS LOS PACIENTES
# --------------------------------------------------

@app.get("/pacientes")
def obtener_pacientes():

    return {
        "mensaje": "Lista de pacientes",
        "pacientes": pacientes
    }


# --------------------------------------------------
# GET - OBTENER UN PACIENTE POR ID
# --------------------------------------------------

@app.get("/pacientes/{paciente_id}")
def obtener_paciente(paciente_id: int):

    for paciente in pacientes:

        if paciente["id"] == paciente_id:

            return paciente

    return {
        "mensaje": "Paciente no encontrado"
    }


# --------------------------------------------------
# POST - CREAR PACIENTE
# --------------------------------------------------

@app.post("/pacientes")
def crear_paciente(paciente: dict):

    nuevo_id = len(pacientes) + 1

    paciente["id"] = nuevo_id

    pacientes.append(paciente)

    return {
        "mensaje": "Paciente creado correctamente",
        "paciente": paciente
    }


# --------------------------------------------------
# PUT - ACTUALIZAR PACIENTE
# --------------------------------------------------

@app.put("/pacientes/{paciente_id}")
def actualizar_paciente(
    paciente_id: int,
    datos: dict
):

    for paciente in pacientes:

        if paciente["id"] == paciente_id:

            paciente["nombre"] = datos.get(
                "nombre",
                paciente["nombre"]
            )

            paciente["edad"] = datos.get(
                "edad",
                paciente["edad"]
            )

            paciente["habitacion"] = datos.get(
                "habitacion",
                paciente["habitacion"]
            )

            return {
                "mensaje": "Paciente actualizado correctamente",
                "paciente": paciente
            }

    return {
        "mensaje": "Paciente no encontrado"
    }


# --------------------------------------------------
# DELETE - ELIMINAR PACIENTE
# --------------------------------------------------

@app.delete("/pacientes/{paciente_id}")
def eliminar_paciente(paciente_id: int):

    for paciente in pacientes:

        if paciente["id"] == paciente_id:

            pacientes.remove(paciente)

            return {
                "mensaje": "Paciente eliminado correctamente"
            }

    return {
        "mensaje": "Paciente no encontrado"
    }