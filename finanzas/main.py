from datetime import date
from typing import Literal

from fastapi import Depends

from comun.aplicacion import crear_servicio
from comun.clientes import obtener_o_none
from comun.config import URL_MEDICO, URL_PACIENTES
from comun.errores import conflicto, datos_invalidos, no_encontrado
from comun.modelos import Id, Mes, Modelo, Monto, Texto, TextoOpcional, en_rango
from comun.repositorio import crear_repositorio
from comun.seguridad import FINANZAS, requiere

# --------------------------------------------------
# CREACIÓN DE LA APLICACIÓN
# --------------------------------------------------

app = crear_servicio(
    titulo="Microservicio de Finanzas",
    descripcion=(
        "Entradas, salidas y manejo de caja: cuentas de los pacientes, cobros, "
        "cuotas familiares, donaciones, gastos y pagos a la fundación"
    ),
    nombre="finanzas"
)

# --------------------------------------------------
# DATOS (en memoria hasta conectar la base de datos)
# --------------------------------------------------

donaciones = crear_repositorio("donaciones", [
    {"tipo_donante": "Empresa nacional", "donante": "Distribuidora La Esperanza",
     "monto": 5000.0, "fecha": "2026-10-01", "descripcion": "Donación mensual",
     "registrado_por": "Datos iniciales"},
    {"tipo_donante": "Persona particular", "donante": "Anónimo",
     "monto": 350.0, "fecha": "2026-10-05", "descripcion": "",
     "registrado_por": "Datos iniciales"},
])

cuotas = crear_repositorio("cuotas", [
    {"paciente_id": 1, "paciente": "Juan Pérez", "mes": "2026-10", "monto": 1200.0,
     "fecha": "2026-10-03", "observaciones": "", "registrado_por": "Datos iniciales"},
])

cobros = crear_repositorio("cobros")

gastos = crear_repositorio("gastos", [
    {"categoria": "Luz", "descripcion": "Factura de energía eléctrica septiembre",
     "monto": 1450.0, "fecha": "2026-10-02", "registrado_por": "Datos iniciales"},
    {"categoria": "Agua", "descripcion": "Servicio de agua septiembre",
     "monto": 320.0, "fecha": "2026-10-02", "registrado_por": "Datos iniciales"},
])

pagos_fundacion = crear_repositorio("pagos_fundacion")

# --------------------------------------------------
# MODELOS
# --------------------------------------------------

TipoDonante = Literal[
    "Empresa internacional", "Empresa nacional", "Gobierno", "Persona particular"
]

CategoriaGasto = Literal[
    "Luz", "Agua", "Alimentación", "Mantenimiento", "Salarios",
    "Medicamentos", "Limpieza", "Otros"
]


class DonacionNueva(Modelo):
    tipo_donante: TipoDonante
    donante: Texto
    monto: Monto
    fecha: date | None = None
    descripcion: TextoOpcional = ""


class CuotaNueva(Modelo):
    paciente_id: Id
    mes: Mes
    monto: Monto
    fecha: date | None = None
    observaciones: TextoOpcional = ""


class CobroNuevo(Modelo):
    paciente_id: Id
    visita_id: Id
    monto: Monto
    fecha: date | None = None
    observaciones: TextoOpcional = ""


class GastoNuevo(Modelo):
    categoria: CategoriaGasto
    descripcion: Texto
    monto: Monto
    fecha: date | None = None


class PagoFundacionNuevo(Modelo):
    monto: Monto
    fecha: date | None = None
    referencia: TextoOpcional = ""


def _registro(datos, usuario):
    registro = datos.model_dump()
    registro["fecha"] = (registro["fecha"] or date.today()).isoformat()
    registro["registrado_por"] = usuario["nombre"]
    return registro


def _filtrar(repositorio, desde, hasta, paciente_id=None):
    lista = repositorio.listar(
        lambda r: en_rango(r["fecha"], desde, hasta) and
        (paciente_id is None or r.get("paciente_id") == paciente_id)
    )
    return sorted(lista, key=lambda r: r["fecha"], reverse=True)


def _total(registros, campo="monto"):
    return round(sum(r[campo] for r in registros), 2)


async def _cargos(paciente_id=None):
    ruta = "/cargos" + (f"?paciente_id={paciente_id}" if paciente_id else "")
    return await obtener_o_none(URL_MEDICO, ruta) or []


async def _paciente_o_error(paciente_id):
    paciente = await obtener_o_none(URL_PACIENTES, f"/pacientes/{paciente_id}")

    if paciente is None:
        raise datos_invalidos("paciente_id", f"El paciente con id {paciente_id} no existe.")

    return paciente


# --------------------------------------------------
# DONACIONES
# --------------------------------------------------

@app.get("/donaciones", tags=["Entradas"])
def listar_donaciones(
    desde: date | None = None,
    hasta: date | None = None,
    usuario: dict = Depends(requiere(FINANZAS))
):
    return _filtrar(donaciones, desde, hasta)


@app.post("/donaciones", status_code=201, tags=["Entradas"])
def registrar_donacion(
    datos: DonacionNueva,
    usuario: dict = Depends(requiere(FINANZAS))
):
    donacion = donaciones.agregar(_registro(datos, usuario))
    return {"mensaje": "Donación registrada correctamente", "donacion": donacion}


# --------------------------------------------------
# CUOTAS MENSUALES DE LOS FAMILIARES
# --------------------------------------------------

@app.get("/cuotas", tags=["Entradas"])
def listar_cuotas(
    paciente_id: int | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    usuario: dict = Depends(requiere(FINANZAS))
):
    return _filtrar(cuotas, desde, hasta, paciente_id)


@app.post("/cuotas", status_code=201, tags=["Entradas"])
async def registrar_cuota(
    datos: CuotaNueva,
    usuario: dict = Depends(requiere(FINANZAS))
):

    paciente = await _paciente_o_error(datos.paciente_id)

    if cuotas.listar(lambda c: c["paciente_id"] == datos.paciente_id and c["mes"] == datos.mes):
        raise conflicto(f"Ya se registró la cuota de {datos.mes} para {paciente['nombre']}.")

    registro = _registro(datos, usuario)
    registro["paciente"] = paciente["nombre"]

    return {"mensaje": "Cuota registrada correctamente", "cuota": cuotas.agregar(registro)}


# --------------------------------------------------
# CUENTAS DE LOS PACIENTES
# Los costos de consultas, exámenes y medicamentos (con el
# descuento de la fundación) se cargan a la cuenta del familiar.
# --------------------------------------------------

def _estado_por_visita(cargos, pagos):
    por_visita = {}

    for cargo in cargos:
        visita = por_visita.setdefault(cargo["visita_id"], {
            "visita_id": cargo["visita_id"], "cargos": [], "total": 0, "pagado": 0
        })
        visita["cargos"].append(cargo)
        visita["total"] = round(visita["total"] + cargo["monto"], 2)

    for pago in pagos:
        if pago["visita_id"] in por_visita:
            visita = por_visita[pago["visita_id"]]
            visita["pagado"] = round(visita["pagado"] + pago["monto"], 2)

    for visita in por_visita.values():
        visita["saldo"] = round(visita["total"] - visita["pagado"], 2)
        visita["estado"] = "Pagada" if visita["saldo"] <= 0 else "Pendiente de pago"
        visita["fecha"] = visita["cargos"][0]["fecha"]

    return sorted(por_visita.values(), key=lambda v: v["fecha"], reverse=True)


@app.get("/cuentas", tags=["Cuentas"])
async def listar_cuentas(usuario: dict = Depends(requiere(FINANZAS))):

    respuesta = await obtener_o_none(URL_PACIENTES, "/pacientes")
    cargos = await _cargos()
    resultado = []

    for paciente in respuesta["pacientes"]:
        total = _total([c for c in cargos if c["paciente_id"] == paciente["id"]])
        pagado = _total(cobros.listar(lambda c: c["paciente_id"] == paciente["id"]))
        resultado.append({
            "paciente_id": paciente["id"],
            "paciente": paciente["nombre"],
            "familiar": paciente.get("familiar_nombre", ""),
            "total_cargos": total,
            "pagado": pagado,
            "saldo": round(total - pagado, 2)
        })

    return resultado


@app.get("/cuentas/visitas", tags=["Cuentas"])
async def visitas_de_todos(usuario: dict = Depends(requiere(FINANZAS))):
    """
    Visitas con sus cargos de todos los pacientes en una sola consulta,
    para el reporte de costos por cita (DEF-17: antes se pedía la
    cuenta de cada paciente una por una).
    """

    respuesta = await obtener_o_none(URL_PACIENTES, "/pacientes")
    cargos = await _cargos()
    pagos = cobros.listar()

    return [{
        "paciente_id": paciente["id"],
        "paciente": paciente["nombre"],
        "visitas": _estado_por_visita(
            [c for c in cargos if c["paciente_id"] == paciente["id"]],
            [p for p in pagos if p["paciente_id"] == paciente["id"]]
        )
    } for paciente in respuesta["pacientes"]]


@app.get("/cuentas/{paciente_id}", tags=["Cuentas"])
async def estado_de_cuenta(
    paciente_id: int,
    usuario: dict = Depends(requiere(FINANZAS))
):

    paciente = await obtener_o_none(URL_PACIENTES, f"/pacientes/{paciente_id}")

    if paciente is None:
        raise no_encontrado("Paciente")

    cargos = await _cargos(paciente_id)
    pagos = cobros.listar(lambda c: c["paciente_id"] == paciente_id)
    visitas = _estado_por_visita(cargos, pagos)

    return {
        "paciente": paciente,
        "visitas": visitas,
        "total_cargos": _total(cargos),
        "pagado": _total(pagos),
        "saldo": round(_total(cargos) - _total(pagos), 2),
        "cuotas": cuotas.listar(lambda c: c["paciente_id"] == paciente_id)
    }


# --------------------------------------------------
# COBROS (pagos del familiar a la cuenta de una cita)
# --------------------------------------------------

@app.get("/cobros", tags=["Entradas"])
def listar_cobros(
    paciente_id: int | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    usuario: dict = Depends(requiere(FINANZAS))
):
    return _filtrar(cobros, desde, hasta, paciente_id)


@app.post("/cobros", status_code=201, tags=["Entradas"])
async def registrar_cobro(
    datos: CobroNuevo,
    usuario: dict = Depends(requiere(FINANZAS))
):

    paciente = await _paciente_o_error(datos.paciente_id)
    cargos = await _cargos(datos.paciente_id)
    pagos = cobros.listar(lambda c: c["paciente_id"] == datos.paciente_id)

    visita = next(
        (v for v in _estado_por_visita(cargos, pagos) if v["visita_id"] == datos.visita_id),
        None
    )

    if visita is None:
        raise datos_invalidos(
            "visita_id", "La visita indicada no tiene cargos para este paciente."
        )

    if datos.monto > visita["saldo"] + 0.001:
        raise datos_invalidos(
            "monto", f"El monto excede el saldo pendiente de la cita (Q{visita['saldo']:.2f})."
        )

    registro = _registro(datos, usuario)
    registro["paciente"] = paciente["nombre"]

    return {"mensaje": "Cobro registrado correctamente", "cobro": cobros.agregar(registro)}


# --------------------------------------------------
# GASTOS
# --------------------------------------------------

@app.get("/gastos", tags=["Salidas"])
def listar_gastos(
    desde: date | None = None,
    hasta: date | None = None,
    usuario: dict = Depends(requiere(FINANZAS))
):
    return _filtrar(gastos, desde, hasta)


@app.post("/gastos", status_code=201, tags=["Salidas"])
def registrar_gasto(
    datos: GastoNuevo,
    usuario: dict = Depends(requiere(FINANZAS))
):
    gasto = gastos.agregar(_registro(datos, usuario))
    return {"mensaje": "Gasto registrado correctamente", "gasto": gasto}


# --------------------------------------------------
# PAGOS A LA FUNDACIÓN
# --------------------------------------------------

async def _estado_fundacion():
    total = _total(await _cargos())
    pagado = _total(pagos_fundacion.listar())
    return {"total_cargos": total, "pagado": pagado, "saldo": round(total - pagado, 2)}


@app.get("/fundacion", tags=["Salidas"])
async def estado_cuenta_fundacion(usuario: dict = Depends(requiere(FINANZAS))):
    return await _estado_fundacion()


@app.get("/pagos-fundacion", tags=["Salidas"])
def listar_pagos_fundacion(
    desde: date | None = None,
    hasta: date | None = None,
    usuario: dict = Depends(requiere(FINANZAS))
):
    return _filtrar(pagos_fundacion, desde, hasta)


@app.post("/pagos-fundacion", status_code=201, tags=["Salidas"])
async def registrar_pago_fundacion(
    datos: PagoFundacionNuevo,
    usuario: dict = Depends(requiere(FINANZAS))
):

    estado = await _estado_fundacion()

    if datos.monto > estado["saldo"] + 0.001:
        raise datos_invalidos(
            "monto", f"El monto excede la deuda con la fundación (Q{estado['saldo']:.2f})."
        )

    pago = pagos_fundacion.agregar(_registro(datos, usuario))
    return {"mensaje": "Pago a la fundación registrado correctamente", "pago": pago}


# --------------------------------------------------
# RESUMEN DE CAJA
# --------------------------------------------------

@app.get("/resumen", tags=["Caja"])
async def resumen_caja(
    desde: date | None = None,
    hasta: date | None = None,
    usuario: dict = Depends(requiere(FINANZAS))
):

    entradas = {
        "donaciones": _total(_filtrar(donaciones, desde, hasta)),
        "cuotas": _total(_filtrar(cuotas, desde, hasta)),
        "cobros": _total(_filtrar(cobros, desde, hasta)),
    }
    salidas = {
        "gastos": _total(_filtrar(gastos, desde, hasta)),
        "pagos_fundacion": _total(_filtrar(pagos_fundacion, desde, hasta)),
    }

    total_entradas = round(sum(entradas.values()), 2)
    total_salidas = round(sum(salidas.values()), 2)

    return {
        "entradas": entradas,
        "salidas": salidas,
        "total_entradas": total_entradas,
        "total_salidas": total_salidas,
        "balance": round(total_entradas - total_salidas, 2),
        "fundacion": await _estado_fundacion()
    }
