from datetime import datetime
from typing import Annotated, Literal

import httpx
from fastapi import Depends, HTTPException
from pydantic import Field

from comun.aplicacion import crear_servicio
from comun.clientes import ServicioNoDisponible, obtener_o_none, pedir
from comun.config import URL_PACIENTES, URL_SOLICITUDES
from comun.errores import conflicto, datos_invalidos, no_encontrado
from comun.modelos import (
    Id, Modelo, Monto, Porcentaje, Texto, TextoLargo, TextoOpcional, normalizar
)
from comun.repositorio import crear_repositorio
from comun.seguridad import (
    EDITAR_CATALOGOS, EDITAR_ENFERMEROS, EDITAR_FICHA, ENTREGAR_MEDICAMENTOS,
    LEER_CATALOGOS, LEER_COSTOS, LEER_FARMACIA, LEER_FICHA, LEER_LABORATORIO,
    LEER_VISITAS, REGISTRAR_RESULTADOS, REGISTRAR_VISITAS, requiere
)

# --------------------------------------------------
# CREACIÓN DE LA APLICACIÓN
# --------------------------------------------------

app = crear_servicio(
    titulo="Microservicio de Atención Médica",
    descripcion=(
        "Médicos, especialidades, enfermeros, ficha e historial médico, "
        "visitas, laboratorio y farmacia de la fundación"
    ),
    nombre="medico"
)

# --------------------------------------------------
# DATOS (en memoria hasta conectar la base de datos)
# --------------------------------------------------

# Registro único (id 1) con el descuento que la fundación da a
# los internos del asilo.
configuracion = crear_repositorio("configuracion", [{"descuento_pct": 25.0}])

especialidades = crear_repositorio("especialidades", [
    {"nombre": "Medicina General", "precio_consulta": 100.0},
    {"nombre": "Cardiología", "precio_consulta": 250.0},
    {"nombre": "Medicina Interna", "precio_consulta": 200.0},
    {"nombre": "Neurología", "precio_consulta": 275.0},
    {"nombre": "Psiquiatría", "precio_consulta": 250.0},
    {"nombre": "Traumatología", "precio_consulta": 225.0},
])

medicos = crear_repositorio("medicos", [
    {"nombre": "Dr. Carlos Méndez", "especialidad_id": 1,
     "colegiado": "12345", "telefono": "5555-0001"},
    {"nombre": "Dra. Ana Ruiz", "especialidad_id": 2,
     "colegiado": "23456", "telefono": "5555-0002"},
    {"nombre": "Dr. Luis García", "especialidad_id": 3,
     "colegiado": "34567", "telefono": "5555-0003"},
    {"nombre": "Dra. Sofía Morales", "especialidad_id": 4,
     "colegiado": "45678", "telefono": "5555-0004"},
])

enfermeros = crear_repositorio("enfermeros", [
    {"nombre": "Rosa Hernández", "turno": "Mañana", "telefono": "5555-0101"},
    {"nombre": "Pedro Sic", "turno": "Tarde", "telefono": "5555-0102"},
])

tipos_examen = crear_repositorio("tipos_examen", [
    {"nombre": "Hematología completa", "precio": 75.0},
    {"nombre": "Glucosa en ayunas", "precio": 30.0},
    {"nombre": "Perfil lipídico", "precio": 90.0},
    {"nombre": "Examen de orina", "precio": 40.0},
    {"nombre": "Electrocardiograma", "precio": 150.0},
])

medicamentos = crear_repositorio("medicamentos", [
    {"nombre": "Losartán 50 mg", "presentacion": "Tableta",
     "precio_unitario": 2.5, "existencia": 300},
    {"nombre": "Metformina 850 mg", "presentacion": "Tableta",
     "precio_unitario": 1.75, "existencia": 250},
    {"nombre": "Acetaminofén 500 mg", "presentacion": "Tableta",
     "precio_unitario": 0.5, "existencia": 500},
    {"nombre": "Omeprazol 20 mg", "presentacion": "Cápsula",
     "precio_unitario": 1.25, "existencia": 200},
])

fichas = crear_repositorio("fichas", [
    {"paciente_id": 1, "tipo_sangre": "O+", "alergias": "Penicilina",
     "psicopatologia": "Ansiedad leve",
     "enfermedades_cronicas": "Hipertensión arterial",
     "medicamentos_base": "Losartán 50 mg cada 24 horas",
     "observaciones": ""},
])

visitas = crear_repositorio("visitas")
examenes = crear_repositorio("examenes")
recetas = crear_repositorio("recetas")


def _con_descuento(precio):
    descuento = configuracion.obtener(1)["descuento_pct"]
    return descuento, round(precio * (1 - descuento / 100), 2)


async def _paciente_o_error(paciente_id):
    paciente = await obtener_o_none(URL_PACIENTES, f"/pacientes/{paciente_id}")

    if paciente is None:
        raise no_encontrado("Paciente")

    return paciente


def _obtener_o_404(repositorio, registro_id, entidad):
    registro = repositorio.obtener(registro_id)

    if registro is None:
        raise no_encontrado(entidad)

    return registro


# --------------------------------------------------
# CATÁLOGOS
# Se crean con una función porque todos tienen las mismas
# operaciones: listar, consultar, crear y actualizar.
# --------------------------------------------------

def registrar_catalogo(ruta, repositorio, entidad, Nuevo, Cambios,
                       roles_editar, validar=None, completar=None):

    completar = completar or (lambda r: r)

    def _validar_nombre(nombre, excepto_id=None):
        for registro in repositorio.listar():
            if registro["id"] != excepto_id and \
                    normalizar(registro["nombre"]) == normalizar(nombre):
                raise conflicto(f"Ya existe un registro con el nombre {registro['nombre']}.")

    @app.get(ruta, tags=["Catálogos"], name=f"listar_{ruta[1:]}")
    def listar(usuario: dict = Depends(requiere(LEER_CATALOGOS))):
        return [completar(r) for r in sorted(repositorio.listar(), key=lambda r: r["nombre"])]

    @app.get(ruta + "/{registro_id}", tags=["Catálogos"], name=f"obtener_{ruta[1:]}")
    def obtener(registro_id: int, usuario: dict = Depends(requiere(LEER_CATALOGOS))):
        return completar(_obtener_o_404(repositorio, registro_id, entidad))

    @app.post(ruta, status_code=201, tags=["Catálogos"], name=f"crear_{ruta[1:]}")
    def crear(datos: Nuevo, usuario: dict = Depends(requiere(roles_editar))):
        registro = datos.model_dump()
        _validar_nombre(registro["nombre"])
        if validar:
            validar(registro)
        return completar(repositorio.agregar(registro))

    @app.put(ruta + "/{registro_id}", tags=["Catálogos"], name=f"actualizar_{ruta[1:]}")
    def actualizar(registro_id: int, datos: Cambios,
                   usuario: dict = Depends(requiere(roles_editar))):
        _obtener_o_404(repositorio, registro_id, entidad)
        cambios = {k: v for k, v in datos.model_dump(exclude_unset=True).items() if v is not None}
        if "nombre" in cambios:
            _validar_nombre(cambios["nombre"], excepto_id=registro_id)
        if validar:
            validar(cambios)
        return completar(repositorio.actualizar(registro_id, cambios))


class EspecialidadNueva(Modelo):
    nombre: Texto
    precio_consulta: Monto


class EspecialidadCambios(Modelo):
    nombre: Texto | None = None
    precio_consulta: Monto | None = None


class MedicoNuevo(Modelo):
    nombre: Texto
    especialidad_id: Id
    colegiado: Texto
    telefono: TextoOpcional = ""


class MedicoCambios(Modelo):
    nombre: Texto | None = None
    especialidad_id: Id | None = None
    colegiado: Texto | None = None
    telefono: TextoOpcional | None = None


Turno = Literal["Mañana", "Tarde", "Noche"]


class EnfermeroNuevo(Modelo):
    nombre: Texto
    turno: Turno
    telefono: TextoOpcional = ""


class EnfermeroCambios(Modelo):
    nombre: Texto | None = None
    turno: Turno | None = None
    telefono: TextoOpcional | None = None


class TipoExamenNuevo(Modelo):
    nombre: Texto
    precio: Monto


class TipoExamenCambios(Modelo):
    nombre: Texto | None = None
    precio: Monto | None = None


Existencia = Annotated[int, Field(ge=0)]


class MedicamentoNuevo(Modelo):
    nombre: Texto
    presentacion: Texto
    precio_unitario: Monto
    existencia: Existencia = 0


class MedicamentoCambios(Modelo):
    nombre: Texto | None = None
    presentacion: Texto | None = None
    precio_unitario: Monto | None = None
    existencia: Existencia | None = None


def _validar_especialidad_de_medico(registro):
    if "especialidad_id" in registro and \
            especialidades.obtener(registro["especialidad_id"]) is None:
        raise datos_invalidos("especialidad_id", "La especialidad indicada no existe.")


def _con_especialidad(medico):
    especialidad = especialidades.obtener(medico["especialidad_id"])
    medico["especialidad"] = especialidad["nombre"] if especialidad else "Sin especialidad"
    return medico


registrar_catalogo("/especialidades", especialidades, "Especialidad",
                   EspecialidadNueva, EspecialidadCambios, EDITAR_CATALOGOS)

registrar_catalogo("/medicos", medicos, "Médico", MedicoNuevo, MedicoCambios,
                   EDITAR_CATALOGOS, validar=_validar_especialidad_de_medico,
                   completar=_con_especialidad)

registrar_catalogo("/enfermeros", enfermeros, "Enfermero(a)",
                   EnfermeroNuevo, EnfermeroCambios, EDITAR_ENFERMEROS)

registrar_catalogo("/tipos-examen", tipos_examen, "Tipo de examen",
                   TipoExamenNuevo, TipoExamenCambios, EDITAR_CATALOGOS)

registrar_catalogo("/medicamentos", medicamentos, "Medicamento",
                   MedicamentoNuevo, MedicamentoCambios, EDITAR_CATALOGOS)


# --------------------------------------------------
# CONFIGURACIÓN - DESCUENTO DE LA FUNDACIÓN
# --------------------------------------------------

class Configuracion(Modelo):
    descuento_pct: Porcentaje


@app.get("/configuracion", tags=["Configuración"])
def obtener_configuracion(usuario: dict = Depends(requiere(LEER_CATALOGOS))):
    return {"descuento_pct": configuracion.obtener(1)["descuento_pct"]}


@app.put("/configuracion", tags=["Configuración"])
def actualizar_configuracion(
    datos: Configuracion,
    usuario: dict = Depends(requiere(EDITAR_CATALOGOS))
):
    configuracion.actualizar(1, datos.model_dump())
    return {"mensaje": "Configuración actualizada", **datos.model_dump()}


# --------------------------------------------------
# FICHA E HISTORIAL MÉDICO
# --------------------------------------------------

class Ficha(Modelo):
    tipo_sangre: TextoOpcional = ""
    alergias: TextoOpcional = ""
    psicopatologia: TextoOpcional = ""
    enfermedades_cronicas: TextoOpcional = ""
    medicamentos_base: TextoOpcional = ""
    observaciones: TextoOpcional = ""


def _ficha_de(paciente_id):
    encontradas = fichas.listar(lambda f: f["paciente_id"] == paciente_id)
    return encontradas[0] if encontradas else None


def _detalle_visita(visita):
    visita["examenes"] = examenes.listar(lambda e: e["visita_id"] == visita["id"])
    visita["recetas"] = recetas.listar(lambda r: r["visita_id"] == visita["id"])
    return visita


def _historial(paciente_id):
    lista = visitas.listar(lambda v: v["paciente_id"] == paciente_id)
    return [_detalle_visita(v) for v in sorted(lista, key=lambda v: v["fecha"], reverse=True)]


@app.get("/fichas/{paciente_id}", tags=["Ficha médica"])
async def obtener_ficha(
    paciente_id: int,
    usuario: dict = Depends(requiere(LEER_FICHA))
):

    paciente = await _paciente_o_error(paciente_id)
    ficha = _ficha_de(paciente_id) or {"paciente_id": paciente_id, **Ficha().model_dump()}

    return {
        "paciente": paciente,
        "ficha": ficha,
        "historial": _historial(paciente_id)
    }


@app.put("/fichas/{paciente_id}", tags=["Ficha médica"])
async def guardar_ficha(
    paciente_id: int,
    datos: Ficha,
    usuario: dict = Depends(requiere(EDITAR_FICHA))
):

    await _paciente_o_error(paciente_id)

    existente = _ficha_de(paciente_id)
    registro = {"paciente_id": paciente_id, **datos.model_dump()}

    if existente:
        ficha = fichas.actualizar(existente["id"], registro)
    else:
        ficha = fichas.agregar(registro)

    return {"mensaje": "Ficha médica guardada correctamente", "ficha": ficha}


@app.get("/historial/{paciente_id}", tags=["Ficha médica"])
async def obtener_historial(
    paciente_id: int,
    usuario: dict = Depends(requiere(LEER_VISITAS))
):

    await _paciente_o_error(paciente_id)
    return _historial(paciente_id)


# --------------------------------------------------
# VISITAS MÉDICAS
# Una solicitud asignada se convierte en visita cuando el
# médico atiende al paciente.
# --------------------------------------------------

class VisitaNueva(Modelo):
    solicitud_id: Id
    diagnostico: TextoLargo
    observaciones: TextoOpcional = ""
    fecha: datetime | None = None


@app.get("/visitas", tags=["Visitas"])
def listar_visitas(
    paciente_id: int | None = None,
    medico_id: int | None = None,
    usuario: dict = Depends(requiere(LEER_VISITAS))
):

    lista = visitas.listar(
        lambda v: (paciente_id is None or v["paciente_id"] == paciente_id) and
        (medico_id is None or v["medico_id"] == medico_id)
    )
    return sorted(lista, key=lambda v: v["fecha"], reverse=True)


@app.get("/visitas/{visita_id}", tags=["Visitas"])
def obtener_visita(
    visita_id: int,
    usuario: dict = Depends(requiere(LEER_VISITAS))
):
    return _detalle_visita(_obtener_o_404(visitas, visita_id, "Visita"))


@app.post("/visitas", status_code=201, tags=["Visitas"])
async def registrar_visita(
    datos: VisitaNueva,
    usuario: dict = Depends(requiere(REGISTRAR_VISITAS))
):

    solicitud = await obtener_o_none(URL_SOLICITUDES, f"/solicitudes/{datos.solicitud_id}")

    if solicitud is None:
        raise datos_invalidos("solicitud_id", "La solicitud indicada no existe.")

    if solicitud["estado"] != "Asignada":
        raise datos_invalidos(
            "solicitud_id",
            f"Solo se puede atender una solicitud asignada; esta está {solicitud['estado']}."
        )

    medico = _con_especialidad(_obtener_o_404(medicos, solicitud["medico_id"], "Médico"))
    especialidad = especialidades.obtener(medico["especialidad_id"])
    descuento, monto = _con_descuento(especialidad["precio_consulta"])

    visita = visitas.agregar({
        "solicitud_id": solicitud["id"],
        "paciente_id": solicitud["paciente_id"],
        "fecha": (datos.fecha or datetime.now()).isoformat(timespec="minutes"),
        "motivo": solicitud["motivo"],
        "medico_id": medico["id"],
        "medico": medico["nombre"],
        "especialidad": medico["especialidad"],
        "enfermero": solicitud.get("enfermero", ""),
        "diagnostico": datos.diagnostico,
        "observaciones": datos.observaciones,
        "registrada_por": usuario["nombre"],
        "precio_regular": especialidad["precio_consulta"],
        "descuento_pct": descuento,
        "costo": monto
    })

    # La solicitud pasa a "Atendida". Si el servicio de solicitudes
    # no responde se deshace la visita para no dejar datos a medias.
    try:
        respuesta = await pedir(
            "PUT", URL_SOLICITUDES, f"/solicitudes/{solicitud['id']}/estado",
            json={"estado": "Atendida", "visita_id": visita["id"]}
        )
        respuesta.raise_for_status()
    except (ServicioNoDisponible, httpx.HTTPStatusError):
        visitas.eliminar(visita["id"])
        raise HTTPException(
            status_code=503,
            detail="No se pudo actualizar la solicitud; la visita no se registró. Intente de nuevo."
        )

    return {"mensaje": "Visita médica registrada correctamente", "visita": _detalle_visita(visita)}


# --------------------------------------------------
# LABORATORIO
# El médico solicita los exámenes en la visita y el
# laboratorio registra el resultado.
# --------------------------------------------------

class ExamenNuevo(Modelo):
    tipo_examen_id: Id
    indicaciones: TextoOpcional = ""


class Resultado(Modelo):
    resultado: TextoLargo


EstadoExamen = Literal["Solicitado", "Completado"]


@app.post("/visitas/{visita_id}/examenes", status_code=201, tags=["Laboratorio"])
def solicitar_examen(
    visita_id: int,
    datos: ExamenNuevo,
    usuario: dict = Depends(requiere(REGISTRAR_VISITAS))
):

    visita = _obtener_o_404(visitas, visita_id, "Visita")
    tipo = tipos_examen.obtener(datos.tipo_examen_id)

    if tipo is None:
        raise datos_invalidos("tipo_examen_id", "El tipo de examen indicado no existe.")

    examen = examenes.agregar({
        "visita_id": visita_id,
        "paciente_id": visita["paciente_id"],
        "tipo_examen_id": tipo["id"],
        "examen": tipo["nombre"],
        "indicaciones": datos.indicaciones,
        "estado": "Solicitado",
        "fecha_solicitud": datetime.now().isoformat(timespec="minutes"),
        "resultado": "",
        "fecha_resultado": None,
        "precio_regular": None,
        "descuento_pct": None,
        "costo": None
    })

    return {"mensaje": "Examen solicitado correctamente", "examen": examen}


@app.get("/examenes", tags=["Laboratorio"])
def listar_examenes(
    paciente_id: int | None = None,
    estado: EstadoExamen | None = None,
    usuario: dict = Depends(requiere(LEER_LABORATORIO))
):

    lista = examenes.listar(
        lambda e: (paciente_id is None or e["paciente_id"] == paciente_id) and
        (estado is None or e["estado"] == estado)
    )
    return sorted(lista, key=lambda e: e["fecha_solicitud"], reverse=True)


@app.put("/examenes/{examen_id}/resultado", tags=["Laboratorio"])
def registrar_resultado(
    examen_id: int,
    datos: Resultado,
    usuario: dict = Depends(requiere(REGISTRAR_RESULTADOS))
):

    examen = _obtener_o_404(examenes, examen_id, "Examen")

    # El precio se fija la primera vez que se registra el resultado.
    cambios = {
        "resultado": datos.resultado,
        "estado": "Completado",
        "fecha_resultado": datetime.now().isoformat(timespec="minutes"),
        "registrado_por": usuario["nombre"]
    }

    if examen["costo"] is None:
        tipo = tipos_examen.obtener(examen["tipo_examen_id"])
        descuento, monto = _con_descuento(tipo["precio"])
        cambios.update(precio_regular=tipo["precio"], descuento_pct=descuento, costo=monto)

    examen = examenes.actualizar(examen_id, cambios)

    return {"mensaje": "Resultado registrado correctamente", "examen": examen}


# --------------------------------------------------
# FARMACIA
# El médico indica el medicamento y la farmacia lo entrega.
# --------------------------------------------------

class RecetaNueva(Modelo):
    medicamento_id: Id
    cantidad: Annotated[int, Field(gt=0, le=1000)]
    indicaciones: Texto
    duracion: Texto


EstadoReceta = Literal["Pendiente de entrega", "Entregado"]


@app.post("/visitas/{visita_id}/recetas", status_code=201, tags=["Farmacia"])
def indicar_medicamento(
    visita_id: int,
    datos: RecetaNueva,
    usuario: dict = Depends(requiere(REGISTRAR_VISITAS))
):

    visita = _obtener_o_404(visitas, visita_id, "Visita")
    medicamento = medicamentos.obtener(datos.medicamento_id)

    if medicamento is None:
        raise datos_invalidos("medicamento_id", "El medicamento indicado no existe.")

    receta = recetas.agregar({
        "visita_id": visita_id,
        "paciente_id": visita["paciente_id"],
        "medicamento_id": medicamento["id"],
        "medicamento": medicamento["nombre"],
        "cantidad": datos.cantidad,
        "indicaciones": datos.indicaciones,
        "duracion": datos.duracion,
        "estado": "Pendiente de entrega",
        "fecha_indicacion": datetime.now().isoformat(timespec="minutes"),
        "fecha_entrega": None,
        "precio_regular": None,
        "descuento_pct": None,
        "costo": None
    })

    return {"mensaje": "Medicamento indicado correctamente", "receta": receta}


@app.get("/recetas", tags=["Farmacia"])
def listar_recetas(
    paciente_id: int | None = None,
    estado: EstadoReceta | None = None,
    usuario: dict = Depends(requiere(LEER_FARMACIA))
):

    lista = recetas.listar(
        lambda r: (paciente_id is None or r["paciente_id"] == paciente_id) and
        (estado is None or r["estado"] == estado)
    )
    return sorted(lista, key=lambda r: r["fecha_indicacion"], reverse=True)


@app.put("/recetas/{receta_id}/entrega", tags=["Farmacia"])
def entregar_medicamento(
    receta_id: int,
    usuario: dict = Depends(requiere(ENTREGAR_MEDICAMENTOS))
):

    receta = _obtener_o_404(recetas, receta_id, "Receta")

    if receta["estado"] == "Entregado":
        raise conflicto("Este medicamento ya fue entregado.")

    medicamento = medicamentos.obtener(receta["medicamento_id"])

    if medicamento["existencia"] < receta["cantidad"]:
        raise conflicto(
            f"No hay existencia suficiente de {medicamento['nombre']}: "
            f"hay {medicamento['existencia']} y se necesitan {receta['cantidad']}."
        )

    medicamentos.actualizar(
        medicamento["id"],
        {"existencia": medicamento["existencia"] - receta["cantidad"]}
    )

    precio = round(medicamento["precio_unitario"] * receta["cantidad"], 2)
    descuento, monto = _con_descuento(precio)

    receta = recetas.actualizar(receta_id, {
        "estado": "Entregado",
        "fecha_entrega": datetime.now().isoformat(timespec="minutes"),
        "entregado_por": usuario["nombre"],
        "precio_regular": precio,
        "descuento_pct": descuento,
        "costo": monto
    })

    return {"mensaje": "Medicamento entregado correctamente", "receta": receta}


# --------------------------------------------------
# CARGOS
# Costos de consultas, exámenes y medicamentos que el asilo
# debe a la fundación y que se cargan a la cuenta del familiar.
# --------------------------------------------------

@app.get("/cargos", tags=["Costos"])
def listar_cargos(
    paciente_id: int | None = None,
    usuario: dict = Depends(requiere(LEER_COSTOS))
):

    def del_paciente(registro):
        return paciente_id is None or registro["paciente_id"] == paciente_id

    cargos = []

    for v in visitas.listar(del_paciente):
        cargos.append({
            "tipo": "Consulta", "visita_id": v["id"], "paciente_id": v["paciente_id"],
            "fecha": v["fecha"], "descripcion": f"Consulta de {v['especialidad']} - {v['medico']}",
            "precio_regular": v["precio_regular"], "descuento_pct": v["descuento_pct"],
            "monto": v["costo"]
        })

    for e in examenes.listar(lambda e: del_paciente(e) and e["estado"] == "Completado"):
        cargos.append({
            "tipo": "Laboratorio", "visita_id": e["visita_id"], "paciente_id": e["paciente_id"],
            "fecha": e["fecha_resultado"], "descripcion": f"Examen: {e['examen']}",
            "precio_regular": e["precio_regular"], "descuento_pct": e["descuento_pct"],
            "monto": e["costo"]
        })

    for r in recetas.listar(lambda r: del_paciente(r) and r["estado"] == "Entregado"):
        cargos.append({
            "tipo": "Farmacia", "visita_id": r["visita_id"], "paciente_id": r["paciente_id"],
            "fecha": r["fecha_entrega"],
            "descripcion": f"Medicamento: {r['medicamento']} x {r['cantidad']}",
            "precio_regular": r["precio_regular"], "descuento_pct": r["descuento_pct"],
            "monto": r["costo"]
        })

    return sorted(cargos, key=lambda c: c["fecha"])
