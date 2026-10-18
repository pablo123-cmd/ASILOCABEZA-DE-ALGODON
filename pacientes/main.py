from datetime import date
from typing import Annotated

from fastapi import Depends, Query
from pydantic import Field

from comun.aplicacion import crear_servicio
from comun.config import EDAD_MAXIMA, EDAD_MINIMA
from comun.errores import conflicto, no_encontrado
from comun.modelos import CorreoOpcional, Modelo, Texto, TextoOpcional, normalizar
from comun.repositorio import RepositorioMemoria
from comun.seguridad import ADMINISTRADOR, EDITAR_PACIENTES, LEER_PACIENTES, requiere

# --------------------------------------------------
# CREACIÓN DE LA APLICACIÓN
# --------------------------------------------------

app = crear_servicio(
    titulo="Microservicio de Pacientes",
    descripcion="Microservicio para administrar los pacientes (internos) del asilo",
    nombre="pacientes"
)

# --------------------------------------------------
# MODELOS
# --------------------------------------------------

Edad = Annotated[int, Field(
    ge=EDAD_MINIMA,
    le=EDAD_MAXIMA,
    description=f"Edad entre {EDAD_MINIMA} y {EDAD_MAXIMA} años"
)]


class PacienteNuevo(Modelo):
    nombre: Texto
    edad: Edad
    habitacion: Texto
    fecha_ingreso: date | None = None
    motivo_ingreso: TextoOpcional = ""
    familiar_nombre: TextoOpcional = ""
    familiar_telefono: TextoOpcional = ""
    familiar_correo: CorreoOpcional = ""


class PacienteCambios(Modelo):
    nombre: Texto | None = None
    edad: Edad | None = None
    habitacion: Texto | None = None
    fecha_ingreso: date | None = None
    motivo_ingreso: TextoOpcional | None = None
    familiar_nombre: TextoOpcional | None = None
    familiar_telefono: TextoOpcional | None = None
    familiar_correo: CorreoOpcional | None = None


# --------------------------------------------------
# DATOS (en memoria hasta conectar la base de datos)
# --------------------------------------------------

pacientes = RepositorioMemoria([
    {
        "nombre": "Juan Pérez",
        "edad": 75,
        "habitacion": "A-01",
        "fecha_ingreso": "2025-03-15",
        "motivo_ingreso": "Hipertensión y necesidad de cuidado permanente",
        "familiar_nombre": "Carlos Pérez",
        "familiar_telefono": "5555-1010",
        "familiar_correo": "carlos.perez@example.com"
    },
    {
        "nombre": "María López",
        "edad": 80,
        "habitacion": "A-02",
        "fecha_ingreso": "2024-11-02",
        "motivo_ingreso": "Diabetes tipo 2 y movilidad reducida",
        "familiar_nombre": "Ana López",
        "familiar_telefono": "5555-2020",
        "familiar_correo": "ana.lopez@example.com"
    }
])


def _verificar_duplicado(nombre, excepto_id=None):
    for paciente in pacientes.listar():
        if paciente["id"] != excepto_id and \
                normalizar(paciente["nombre"]) == normalizar(nombre):
            raise conflicto(
                f"Ya existe un paciente registrado con el nombre "
                f"{paciente['nombre']} (id {paciente['id']})."
            )


def _a_registro(datos):
    if datos.get("fecha_ingreso") is not None:
        datos["fecha_ingreso"] = datos["fecha_ingreso"].isoformat()
    return datos


# --------------------------------------------------
# GET - LISTAR Y BUSCAR PACIENTES
# --------------------------------------------------

@app.get("/pacientes", tags=["Pacientes"])
def obtener_pacientes(
    buscar: str = Query("", description="Texto a buscar en nombre o habitación"),
    usuario: dict = Depends(requiere(LEER_PACIENTES))
):

    texto = normalizar(buscar)

    resultado = pacientes.listar(
        lambda p: texto in normalizar(p["nombre"]) or
        texto in normalizar(p["habitacion"])
    )

    return {
        "mensaje": "Lista de pacientes",
        "pacientes": sorted(resultado, key=lambda p: p["nombre"])
    }


# --------------------------------------------------
# GET - OBTENER UN PACIENTE POR ID
# --------------------------------------------------

@app.get("/pacientes/{paciente_id}", tags=["Pacientes"])
def obtener_paciente(
    paciente_id: int,
    usuario: dict = Depends(requiere(LEER_PACIENTES))
):

    paciente = pacientes.obtener(paciente_id)

    if paciente is None:
        raise no_encontrado("Paciente")

    return paciente


# --------------------------------------------------
# POST - CREAR PACIENTE
# --------------------------------------------------

@app.post("/pacientes", status_code=201, tags=["Pacientes"])
def crear_paciente(
    datos: PacienteNuevo,
    usuario: dict = Depends(requiere(EDITAR_PACIENTES))
):

    _verificar_duplicado(datos.nombre)

    registro = _a_registro(datos.model_dump())
    registro["fecha_ingreso"] = registro["fecha_ingreso"] or date.today().isoformat()

    paciente = pacientes.agregar(registro)

    return {
        "mensaje": "Paciente creado correctamente",
        "paciente": paciente
    }


# --------------------------------------------------
# PUT - ACTUALIZAR PACIENTE
# Solo se modifican los campos enviados.
# --------------------------------------------------

@app.put("/pacientes/{paciente_id}", tags=["Pacientes"])
def actualizar_paciente(
    paciente_id: int,
    datos: PacienteCambios,
    usuario: dict = Depends(requiere(EDITAR_PACIENTES))
):

    if pacientes.obtener(paciente_id) is None:
        raise no_encontrado("Paciente")

    cambios = _a_registro({
        campo: valor
        for campo, valor in datos.model_dump(exclude_unset=True).items()
        if valor is not None
    })

    if "nombre" in cambios:
        _verificar_duplicado(cambios["nombre"], excepto_id=paciente_id)

    paciente = pacientes.actualizar(paciente_id, cambios)

    return {
        "mensaje": "Paciente actualizado correctamente",
        "paciente": paciente
    }


# --------------------------------------------------
# DELETE - ELIMINAR PACIENTE
# --------------------------------------------------

@app.delete("/pacientes/{paciente_id}", tags=["Pacientes"])
def eliminar_paciente(
    paciente_id: int,
    usuario: dict = Depends(requiere((ADMINISTRADOR,)))
):

    if not pacientes.eliminar(paciente_id):
        raise no_encontrado("Paciente")

    return {
        "mensaje": "Paciente eliminado correctamente"
    }
