"""Casos del plan SQA para los módulos médicos y financieros (sección F)."""

import pytest

from comun.config import URL_FINANZAS, URL_MEDICO, URL_SOLICITUDES
from comun.seguridad import (
    ESPECIALISTA, FARMACIA, FINANCIERO, FUNDACION, LABORATORIO, PERSONAL
)


@pytest.fixture
def visita(api):
    """Atiende la solicitud 2 (asignada en los datos iniciales)."""

    respuesta = api(URL_MEDICO, ESPECIALISTA).post(
        "/visitas", json={"solicitud_id": 2, "diagnostico": "Diabetes controlada"}
    )
    assert respuesta.status_code == 201, respuesta.json()
    return respuesta.json()["visita"]


def test_cp38_ficha_medica(api):
    cliente = api(URL_MEDICO, ESPECIALISTA)

    respuesta = cliente.put("/fichas/2", json={"tipo_sangre": "A+", "alergias": "Ninguna"})
    ficha = cliente.get("/fichas/2").json()

    assert respuesta.status_code == 200
    assert ficha["ficha"]["tipo_sangre"] == "A+"
    assert ficha["paciente"]["nombre"] == "María López"


def test_ficha_de_paciente_inexistente(api):
    assert api(URL_MEDICO, ESPECIALISTA).get("/fichas/999").status_code == 404


def test_cp40_medicos_y_especialidades(api):
    cliente = api(URL_MEDICO, FUNDACION)

    especialidad = cliente.post(
        "/especialidades", json={"nombre": "Geriatría", "precio_consulta": 180}
    ).json()
    medico = cliente.post("/medicos", json={
        "nombre": "Dr. Mario Paz", "especialidad_id": especialidad["id"], "colegiado": "999"
    }).json()

    assert medico["especialidad"] == "Geriatría"
    assert cliente.post("/especialidades", json={
        "nombre": "geriatría", "precio_consulta": 1
    }).status_code == 409


def test_cp41_visita_queda_en_historial_y_solicitud_atendida(api, visita):
    historial = api(URL_MEDICO, ESPECIALISTA).get("/historial/2").json()
    solicitud = api(URL_SOLICITUDES, FUNDACION).get("/solicitudes/2").json()

    assert historial[0]["diagnostico"] == "Diabetes controlada"
    assert solicitud["estado"] == "Atendida"
    assert solicitud["visita_id"] == visita["id"]
    assert visita["costo"] == 150.0  # 200 de Medicina Interna con 25 % de descuento


def test_visita_solo_para_solicitud_asignada(api):
    respuesta = api(URL_MEDICO, ESPECIALISTA).post(
        "/visitas", json={"solicitud_id": 1, "diagnostico": "x"}
    )

    assert respuesta.status_code == 422


def test_cp42_laboratorio(api, visita):
    medico = api(URL_MEDICO, ESPECIALISTA)
    laboratorio = api(URL_MEDICO, LABORATORIO)

    examen = medico.post(
        f"/visitas/{visita['id']}/examenes", json={"tipo_examen_id": 2}
    ).json()["examen"]
    pendientes = laboratorio.get("/examenes", params={"estado": "Solicitado"}).json()
    resultado = laboratorio.put(
        f"/examenes/{examen['id']}/resultado", json={"resultado": "Glucosa 110 mg/dL"}
    ).json()["examen"]

    assert [e["id"] for e in pendientes] == [examen["id"]]
    assert resultado["estado"] == "Completado"
    assert resultado["costo"] == 22.5
    assert medico.get(f"/visitas/{visita['id']}").json()["examenes"][0]["resultado"] == "Glucosa 110 mg/dL"


def test_cp43_farmacia(api, visita):
    medico = api(URL_MEDICO, ESPECIALISTA)
    farmacia = api(URL_MEDICO, FARMACIA)

    receta = medico.post(f"/visitas/{visita['id']}/recetas", json={
        "medicamento_id": 2, "cantidad": 30,
        "indicaciones": "Una tableta con el desayuno", "duracion": "30 días"
    }).json()["receta"]
    entregada = farmacia.put(f"/recetas/{receta['id']}/entrega").json()["receta"]

    assert entregada["estado"] == "Entregado"
    assert entregada["costo"] == round(1.75 * 30 * 0.75, 2)
    assert farmacia.put(f"/recetas/{receta['id']}/entrega").status_code == 409
    assert farmacia.get("/medicamentos/2").json()["existencia"] == 220


def test_farmacia_sin_existencia(api, visita):
    receta = api(URL_MEDICO, ESPECIALISTA).post(f"/visitas/{visita['id']}/recetas", json={
        "medicamento_id": 4, "cantidad": 999, "indicaciones": "x", "duracion": "x"
    }).json()["receta"]

    assert api(URL_MEDICO, FARMACIA).put(f"/recetas/{receta['id']}/entrega").status_code == 409


def test_cp44_costos_y_cuentas_pendientes(api, visita):
    finanzas = api(URL_FINANZAS, FINANCIERO)

    cuenta = finanzas.get("/cuentas/2").json()
    assert cuenta["saldo"] == 150.0
    assert cuenta["visitas"][0]["estado"] == "Pendiente de pago"

    exceso = finanzas.post("/cobros", json={"paciente_id": 2, "visita_id": visita["id"], "monto": 500})
    assert exceso.status_code == 422

    finanzas.post("/cobros", json={"paciente_id": 2, "visita_id": visita["id"], "monto": 150})
    cuenta = finanzas.get("/cuentas/2").json()
    assert cuenta["saldo"] == 0
    assert cuenta["visitas"][0]["estado"] == "Pagada"


def test_cp45_donaciones_cuotas_gastos_y_pagos(api, visita):
    finanzas = api(URL_FINANZAS, FINANCIERO)

    assert finanzas.post("/donaciones", json={
        "tipo_donante": "Gobierno", "donante": "Municipalidad", "monto": 1000, "fecha": "2026-10-15"
    }).status_code == 201
    assert finanzas.post("/cuotas", json={"paciente_id": 2, "mes": "2026-10", "monto": 1200}).status_code == 201
    assert finanzas.post("/cuotas", json={"paciente_id": 2, "mes": "2026-10", "monto": 1200}).status_code == 409
    assert finanzas.post("/cuotas", json={"paciente_id": 2, "mes": "2026-13", "monto": 1}).status_code == 422
    assert finanzas.post("/gastos", json={"categoria": "Agua", "descripcion": "Octubre", "monto": 300}).status_code == 201
    assert finanzas.post("/pagos-fundacion", json={"monto": 9999}).status_code == 422
    assert finanzas.post("/pagos-fundacion", json={"monto": 100}).status_code == 201

    donaciones = finanzas.get("/donaciones", params={"desde": "2026-10-15", "hasta": "2026-10-15"}).json()
    assert [d["donante"] for d in donaciones] == ["Municipalidad"]
    assert finanzas.get("/fundacion").json()["saldo"] == 50.0


def test_finanzas_solo_encargado_financiero(api):
    assert api(URL_FINANZAS, PERSONAL).get("/donaciones").status_code == 403
    assert api(URL_FINANZAS).get("/donaciones").status_code == 401


def test_descuento_configurable(api):
    fundacion = api(URL_MEDICO, FUNDACION)

    assert fundacion.put("/configuracion", json={"descuento_pct": 150}).status_code == 422
    assert fundacion.put("/configuracion", json={"descuento_pct": 40}).json()["descuento_pct"] == 40
