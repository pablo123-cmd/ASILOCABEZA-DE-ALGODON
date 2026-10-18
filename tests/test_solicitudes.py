"""Casos del plan SQA para solicitudes y asignaciones (secciones C y D)."""

from datetime import datetime, timedelta

from comun.config import URL_SOLICITUDES
from comun.seguridad import ENFERMERO, FUNDACION, MEDICO_GENERAL

NUEVA = {"paciente_id": 1, "especialidad": "Neurología", "motivo": "Pérdida de memoria"}


def test_especialidad_sin_acentos_se_reconoce(api):
    respuesta = api(URL_SOLICITUDES, MEDICO_GENERAL).post(
        "/solicitudes", json={**NUEVA, "especialidad": "neurologia"}
    )

    assert respuesta.json()["solicitud"]["especialidad"] == "Neurología"

MANANA = (datetime.now() + timedelta(days=1)).replace(second=0, microsecond=0)


def test_cp21_listado_de_solicitudes(api):
    lista = api(URL_SOLICITUDES, ENFERMERO).get("/solicitudes").json()["solicitudes"]

    assert len(lista) == 2
    assert {"paciente", "especialidad", "motivo", "estado"} <= set(lista[0])


def test_cp22_crear_solicitud_valida(api):
    respuesta = api(URL_SOLICITUDES, MEDICO_GENERAL).post("/solicitudes", json=NUEVA)

    assert respuesta.status_code == 201
    solicitud = respuesta.json()["solicitud"]
    assert solicitud["estado"] == "Pendiente"
    assert solicitud["paciente"] == "Juan Pérez"


def test_cp23_paciente_inexistente(api):
    respuesta = api(URL_SOLICITUDES, MEDICO_GENERAL).post(
        "/solicitudes", json={**NUEVA, "paciente_id": 999}
    )

    assert respuesta.status_code == 422
    assert "no existe" in respuesta.json()["mensaje"]


def test_cp24_campos_obligatorios(api):
    respuesta = api(URL_SOLICITUDES, MEDICO_GENERAL).post(
        "/solicitudes", json={"paciente_id": 1, "especialidad": " ", "motivo": ""}
    )

    assert respuesta.status_code == 422


def test_cp25_especialidad_fuera_de_catalogo(api):
    respuesta = api(URL_SOLICITUDES, MEDICO_GENERAL).post(
        "/solicitudes", json={**NUEVA, "especialidad": "Astrología"}
    )

    assert respuesta.status_code == 422
    assert "no está registrada" in respuesta.json()["mensaje"]


def test_cp26_asignacion_cambia_a_asignada(api):
    respuesta = api(URL_SOLICITUDES, FUNDACION).put(
        "/solicitudes/1/asignacion",
        json={"medico_id": 2, "horario": MANANA.isoformat()}
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["solicitud"]["estado"] == "Asignada"


def test_cp27_estado_invalido(api):
    cliente = api(URL_SOLICITUDES, FUNDACION)

    assert cliente.put("/solicitudes/1/estado", json={"estado": "Inventado"}).status_code == 422
    assert cliente.put("/solicitudes/1/estado", json={"estado": "Atendida"}).status_code == 422


def test_cp28_asignacion_medico_horario_enfermero(api):
    respuesta = api(URL_SOLICITUDES, FUNDACION).put(
        "/solicitudes/1/asignacion",
        json={"medico_id": 2, "horario": MANANA.isoformat(), "enfermero_id": 2}
    )

    solicitud = respuesta.json()["solicitud"]
    assert solicitud["medico"] == "Dra. Ana Ruiz"
    assert solicitud["enfermero"] == "Pedro Sic"
    assert solicitud["horario"] == MANANA.isoformat(timespec="minutes")


def test_asignacion_rechaza_medico_de_otra_especialidad(api):
    respuesta = api(URL_SOLICITUDES, FUNDACION).put(
        "/solicitudes/1/asignacion",
        json={"medico_id": 1, "horario": MANANA.isoformat()}
    )

    assert respuesta.status_code == 422


def test_asignacion_rechaza_horario_ocupado(api):
    medico_general = api(URL_SOLICITUDES, MEDICO_GENERAL)
    fundacion = api(URL_SOLICITUDES, FUNDACION)
    otra = medico_general.post(
        "/solicitudes", json={**NUEVA, "especialidad": "Cardiología"}
    ).json()["solicitud"]
    asignacion = {"medico_id": 2, "horario": MANANA.isoformat()}

    fundacion.put("/solicitudes/1/asignacion", json=asignacion)
    respuesta = fundacion.put(f"/solicitudes/{otra['id']}/asignacion", json=asignacion)

    assert respuesta.status_code == 409


def test_asignar_enfermero(api):
    respuesta = api(URL_SOLICITUDES, MEDICO_GENERAL).put(
        "/solicitudes/1/enfermero", json={"enfermero_id": 2}
    )

    assert respuesta.json()["solicitud"]["enfermero"] == "Pedro Sic"


def test_cp47_correo_al_familiar_al_crear_solicitud(api):
    cliente = api(URL_SOLICITUDES, MEDICO_GENERAL)

    cliente.post("/solicitudes", json=NUEVA)
    correos = cliente.get("/notificaciones").json()

    assert correos[0]["destinatario"] == "carlos.perez@example.com"
    assert "Neurología" in correos[0]["cuerpo"]
    assert correos[0]["estado"].startswith("Simulado")


def test_solicitud_404(api):
    assert api(URL_SOLICITUDES, FUNDACION).get("/solicitudes/999").status_code == 404


def test_solicitudes_sin_sesion(api):
    assert api(URL_SOLICITUDES).get("/solicitudes").status_code == 401
