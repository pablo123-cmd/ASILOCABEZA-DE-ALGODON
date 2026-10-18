from datetime import datetime
from typing import Literal

from fastapi import Depends

from comun.aplicacion import crear_servicio
from comun.clientes import obtener_o_none
from comun.config import URL_MEDICO, URL_PACIENTES
from comun.correo import enviar_correo
from comun.errores import conflicto, datos_invalidos, no_encontrado
from comun.modelos import Id, Modelo, Texto, TextoLargo, normalizar
from comun.repositorio import RepositorioMemoria
from comun.seguridad import (
    ADMINISTRADOR, ASIGNAR_ENFERMERO, ASIGNAR_MEDICO, CANCELAR_SOLICITUDES,
    CREAR_SOLICITUDES, LEER_SOLICITUDES, SERVICIO, VER_NOTIFICACIONES,
    requiere
)

# ==================================================
# CREACIÓN DE LA APLICACIÓN
# ==================================================

app = crear_servicio(
    titulo="Microservicio de Solicitudes Médicas",
    descripcion=(
        "Solicitudes de referencia del médico general a un especialista, "
        "con asignación de enfermero, médico y horario"
    ),
    nombre="solicitudes"
)

# ==================================================
# ESTADOS DE UNA SOLICITUD
# Pendiente -> Asignada -> Atendida
# Pendiente o Asignada -> Cancelada
# ==================================================

Estado = Literal["Pendiente", "Asignada", "Atendida", "Cancelada"]

# ==================================================
# DATOS (en memoria hasta conectar la base de datos)
# ==================================================

solicitudes = RepositorioMemoria([
    {
        "paciente_id": 1,
        "paciente": "Juan Pérez",
        "especialidad_id": 2,
        "especialidad": "Cardiología",
        "motivo": "Dolor en el pecho",
        "estado": "Pendiente",
        "enfermero_id": 1,
        "enfermero": "Rosa Hernández",
        "medico_id": None,
        "medico": "",
        "horario": None,
        "visita_id": None,
        "fecha_creacion": "2026-10-10T08:30",
        "creada_por": "Médico general"
    },
    {
        "paciente_id": 2,
        "paciente": "María López",
        "especialidad_id": 3,
        "especialidad": "Medicina Interna",
        "motivo": "Control médico",
        "estado": "Asignada",
        "enfermero_id": 2,
        "enfermero": "Pedro Sic",
        "medico_id": 3,
        "medico": "Dr. Luis García",
        "horario": "2026-10-22T09:00",
        "visita_id": None,
        "fecha_creacion": "2026-10-09T10:15",
        "creada_por": "Médico general"
    }
])

# Registro de los correos enviados (o simulados) a los familiares.
notificaciones = RepositorioMemoria()


# ==================================================
# MODELOS
# ==================================================

class SolicitudNueva(Modelo):
    paciente_id: Id
    especialidad: Texto
    motivo: TextoLargo
    enfermero_id: Id | None = None


class SolicitudCambios(Modelo):
    especialidad: Texto | None = None
    motivo: TextoLargo | None = None


class Asignacion(Modelo):
    medico_id: Id
    horario: datetime
    enfermero_id: Id | None = None


class AsignacionEnfermero(Modelo):
    enfermero_id: Id


class CambioEstado(Modelo):
    estado: Estado
    visita_id: Id | None = None


# ==================================================
# VALIDACIONES CON OTROS SERVICIOS
# ==================================================

def _obtener_o_404(solicitud_id):
    solicitud = solicitudes.obtener(solicitud_id)

    if solicitud is None:
        raise no_encontrado("Solicitud")

    return solicitud


async def _validar_paciente(paciente_id):
    paciente = await obtener_o_none(URL_PACIENTES, f"/pacientes/{paciente_id}")

    if paciente is None:
        raise datos_invalidos(
            "paciente_id", f"El paciente con id {paciente_id} no existe."
        )

    return paciente


async def _validar_especialidad(nombre):
    catalogo = await obtener_o_none(URL_MEDICO, "/especialidades")

    for especialidad in catalogo or []:
        if normalizar(especialidad["nombre"]) == normalizar(nombre):
            return especialidad

    opciones = ", ".join(e["nombre"] for e in catalogo or [])
    raise datos_invalidos(
        "especialidad",
        f"La especialidad «{nombre}» no está registrada. Opciones: {opciones}."
    )


async def _validar_enfermero(enfermero_id):
    enfermero = await obtener_o_none(URL_MEDICO, f"/enfermeros/{enfermero_id}")

    if enfermero is None:
        raise datos_invalidos("enfermero_id", "El enfermero(a) indicado no existe.")

    return enfermero


async def _notificar_familiar(solicitud, asunto, cuerpo):
    paciente = await obtener_o_none(URL_PACIENTES, f"/pacientes/{solicitud['paciente_id']}")
    paciente = paciente or {}

    destinatario = paciente.get("familiar_correo", "")
    saludo = f"Estimado(a) {paciente.get('familiar_nombre') or 'familiar'}:\n\n"

    estado = await enviar_correo(destinatario, asunto, saludo + cuerpo)

    notificaciones.agregar({
        "solicitud_id": solicitud["id"],
        "paciente": solicitud["paciente"],
        "destinatario": destinatario,
        "asunto": asunto,
        "cuerpo": saludo + cuerpo,
        "estado": estado,
        "fecha": datetime.now().isoformat(timespec="minutes")
    })


# ==================================================
# GET - LISTAR SOLICITUDES
# ==================================================

@app.get("/solicitudes", tags=["Solicitudes"])
def obtener_solicitudes(
    paciente_id: int | None = None,
    estado: Estado | None = None,
    medico_id: int | None = None,
    usuario: dict = Depends(requiere(LEER_SOLICITUDES))
):

    lista = solicitudes.listar(
        lambda s: (paciente_id is None or s["paciente_id"] == paciente_id) and
        (estado is None or s["estado"] == estado) and
        (medico_id is None or s["medico_id"] == medico_id)
    )

    return {
        "mensaje": "Lista de solicitudes",
        "solicitudes": sorted(lista, key=lambda s: s["fecha_creacion"], reverse=True)
    }


# ==================================================
# GET - OBTENER UNA SOLICITUD POR ID
# ==================================================

@app.get("/solicitudes/{solicitud_id}", tags=["Solicitudes"])
def obtener_solicitud(
    solicitud_id: int,
    usuario: dict = Depends(requiere(LEER_SOLICITUDES))
):
    return _obtener_o_404(solicitud_id)


# ==================================================
# POST - CREAR SOLICITUD (médico general)
# ==================================================

@app.post("/solicitudes", status_code=201, tags=["Solicitudes"])
async def crear_solicitud(
    datos: SolicitudNueva,
    usuario: dict = Depends(requiere(CREAR_SOLICITUDES))
):

    paciente = await _validar_paciente(datos.paciente_id)
    especialidad = await _validar_especialidad(datos.especialidad)
    enfermero = await _validar_enfermero(datos.enfermero_id) if datos.enfermero_id else None

    solicitud = solicitudes.agregar({
        "paciente_id": paciente["id"],
        "paciente": paciente["nombre"],
        "especialidad_id": especialidad["id"],
        "especialidad": especialidad["nombre"],
        "motivo": datos.motivo,
        "estado": "Pendiente",
        "enfermero_id": enfermero["id"] if enfermero else None,
        "enfermero": enfermero["nombre"] if enfermero else "",
        "medico_id": None,
        "medico": "",
        "horario": None,
        "visita_id": None,
        "fecha_creacion": datetime.now().isoformat(timespec="minutes"),
        "creada_por": usuario["nombre"]
    })

    await _notificar_familiar(
        solicitud,
        f"Solicitud médica para {paciente['nombre']}",
        f"Le informamos que {paciente['nombre']} fue evaluado(a) por el médico "
        f"general y referido(a) a la especialidad de {especialidad['nombre']}.\n\n"
        f"Motivo: {datos.motivo}\n"
        f"Estado: pendiente de asignación de médico y horario por la fundación.\n\n"
        f"Le enviaremos otro aviso cuando se asigne el médico.\n\n"
        f"Asilo Cabeza de Algodón"
    )

    return {
        "mensaje": "Solicitud creada correctamente",
        "solicitud": solicitud
    }


# ==================================================
# PUT - MODIFICAR MOTIVO O ESPECIALIDAD
# Solo mientras la solicitud está pendiente.
# ==================================================

@app.put("/solicitudes/{solicitud_id}", tags=["Solicitudes"])
async def actualizar_solicitud(
    solicitud_id: int,
    datos: SolicitudCambios,
    usuario: dict = Depends(requiere(CREAR_SOLICITUDES))
):

    solicitud = _obtener_o_404(solicitud_id)

    if solicitud["estado"] != "Pendiente":
        raise conflicto("Solo se puede modificar una solicitud pendiente.")

    cambios = {}

    if datos.motivo is not None:
        cambios["motivo"] = datos.motivo

    if datos.especialidad is not None:
        especialidad = await _validar_especialidad(datos.especialidad)
        cambios.update(especialidad_id=especialidad["id"], especialidad=especialidad["nombre"])

    return {
        "mensaje": "Solicitud actualizada correctamente",
        "solicitud": solicitudes.actualizar(solicitud_id, cambios)
    }


# ==================================================
# PUT - ASIGNAR ENFERMERO(A) ACOMPAÑANTE (médico general)
# ==================================================

@app.put("/solicitudes/{solicitud_id}/enfermero", tags=["Asignaciones"])
async def asignar_enfermero(
    solicitud_id: int,
    datos: AsignacionEnfermero,
    usuario: dict = Depends(requiere(ASIGNAR_ENFERMERO))
):

    solicitud = _obtener_o_404(solicitud_id)

    if solicitud["estado"] in ("Atendida", "Cancelada"):
        raise conflicto(f"La solicitud ya está {solicitud['estado'].lower()}.")

    enfermero = await _validar_enfermero(datos.enfermero_id)

    return {
        "mensaje": "Enfermero(a) asignado correctamente",
        "solicitud": solicitudes.actualizar(
            solicitud_id,
            {"enfermero_id": enfermero["id"], "enfermero": enfermero["nombre"]}
        )
    }


# ==================================================
# PUT - ASIGNAR MÉDICO Y HORARIO (fundación)
# ==================================================

@app.put("/solicitudes/{solicitud_id}/asignacion", tags=["Asignaciones"])
async def asignar_medico(
    solicitud_id: int,
    datos: Asignacion,
    usuario: dict = Depends(requiere(ASIGNAR_MEDICO))
):

    solicitud = _obtener_o_404(solicitud_id)

    if solicitud["estado"] not in ("Pendiente", "Asignada"):
        raise conflicto(f"La solicitud ya está {solicitud['estado'].lower()}.")

    medico = await obtener_o_none(URL_MEDICO, f"/medicos/{datos.medico_id}")

    if medico is None:
        raise datos_invalidos("medico_id", "El médico indicado no existe.")

    if medico["especialidad_id"] != solicitud["especialidad_id"]:
        raise datos_invalidos(
            "medico_id",
            f"{medico['nombre']} es de {medico['especialidad']}; "
            f"la solicitud requiere {solicitud['especialidad']}."
        )

    if datos.horario <= datetime.now():
        raise datos_invalidos("horario", "El horario debe ser una fecha futura.")

    horario = datos.horario.isoformat(timespec="minutes")

    ocupado = solicitudes.listar(
        lambda s: s["id"] != solicitud_id and s["estado"] == "Asignada" and
        s["medico_id"] == medico["id"] and s["horario"] == horario
    )

    if ocupado:
        raise conflicto(f"{medico['nombre']} ya tiene un paciente asignado en ese horario.")

    cambios = {
        "medico_id": medico["id"],
        "medico": medico["nombre"],
        "horario": horario,
        "estado": "Asignada"
    }

    if datos.enfermero_id:
        enfermero = await _validar_enfermero(datos.enfermero_id)
        cambios.update(enfermero_id=enfermero["id"], enfermero=enfermero["nombre"])

    solicitud = solicitudes.actualizar(solicitud_id, cambios)

    await _notificar_familiar(
        solicitud,
        f"Cita asignada para {solicitud['paciente']}",
        f"La fundación asignó la cita de {solicitud['paciente']} en la especialidad "
        f"de {solicitud['especialidad']}.\n\n"
        f"Médico: {medico['nombre']}\n"
        f"Fecha y hora: {datos.horario.strftime('%d/%m/%Y %H:%M')}\n"
        f"Enfermero(a) acompañante: {solicitud['enfermero'] or 'por asignar'}\n\n"
        f"Asilo Cabeza de Algodón"
    )

    return {
        "mensaje": "Médico y horario asignados correctamente",
        "solicitud": solicitud
    }


# ==================================================
# PUT - CAMBIAR ESTADO
# "Asignada" solo se obtiene con la asignación de médico y horario,
# y "Atendida" la registra el servicio médico al crear la visita.
# ==================================================

@app.put("/solicitudes/{solicitud_id}/estado", tags=["Solicitudes"])
def cambiar_estado(
    solicitud_id: int,
    datos: CambioEstado,
    usuario: dict = Depends(requiere(CANCELAR_SOLICITUDES))
):

    solicitud = _obtener_o_404(solicitud_id)
    actual = solicitud["estado"]

    if actual in ("Atendida", "Cancelada"):
        raise conflicto(f"La solicitud ya está {actual.lower()} y no puede cambiar de estado.")

    if datos.estado == "Asignada":
        raise datos_invalidos(
            "estado", "Para asignar la solicitud indique médico y horario en /asignacion."
        )

    if datos.estado == "Pendiente":
        raise datos_invalidos("estado", "Una solicitud no puede regresar a pendiente.")

    if datos.estado == "Atendida":
        if usuario["rol"] != SERVICIO:
            raise datos_invalidos(
                "estado", "La solicitud se marca como atendida al registrar la visita médica."
            )
        if actual != "Asignada":
            raise conflicto("Solo una solicitud asignada puede marcarse como atendida.")

    cambios = {"estado": datos.estado}
    if datos.visita_id:
        cambios["visita_id"] = datos.visita_id

    return {
        "mensaje": f"La solicitud ahora está {datos.estado.lower()}",
        "solicitud": solicitudes.actualizar(solicitud_id, cambios)
    }


# ==================================================
# DELETE - ELIMINAR SOLICITUD (administrador)
# ==================================================

@app.delete("/solicitudes/{solicitud_id}", tags=["Solicitudes"])
def eliminar_solicitud(
    solicitud_id: int,
    usuario: dict = Depends(requiere((ADMINISTRADOR,)))
):

    if not solicitudes.eliminar(solicitud_id):
        raise no_encontrado("Solicitud")

    return {
        "mensaje": "Solicitud eliminada correctamente"
    }


# ==================================================
# GET - CORREOS ENVIADOS A FAMILIARES
# ==================================================

@app.get("/notificaciones", tags=["Notificaciones"])
def obtener_notificaciones(
    usuario: dict = Depends(requiere(VER_NOTIFICACIONES))
):
    return sorted(notificaciones.listar(), key=lambda n: n["id"], reverse=True)
