"""Casos del plan SQA para el microservicio de pacientes (sección B)."""

from comun.config import URL_PACIENTES
from comun.seguridad import ADMINISTRADOR, FARMACIA, PERSONAL

NUEVO = {"nombre": "Pedro Gómez", "edad": 70, "habitacion": "B-01"}


def test_cp06_registro_desde_el_microservicio(api):
    cliente = api(URL_PACIENTES, PERSONAL)

    respuesta = cliente.post("/pacientes", json=NUEVO)

    assert respuesta.status_code == 201
    paciente = respuesta.json()["paciente"]
    assert cliente.get(f"/pacientes/{paciente['id']}").json()["nombre"] == "Pedro Gómez"


def test_cp08_envio_vacio_mensaje_comprensible(api):
    respuesta = api(URL_PACIENTES, PERSONAL).post("/pacientes", json={})

    assert respuesta.status_code == 422
    cuerpo = respuesta.json()
    assert cuerpo["mensaje"] == "Los datos enviados no son válidos."
    assert {"campo": "nombre", "mensaje": "Este campo es obligatorio."} in cuerpo["errores"]


def test_cp09_campos_con_solo_espacios(api):
    respuesta = api(URL_PACIENTES, PERSONAL).post(
        "/pacientes", json={**NUEVO, "nombre": "   ", "habitacion": "  "}
    )

    assert respuesta.status_code == 422
    campos = {e["campo"] for e in respuesta.json()["errores"]}
    assert campos == {"nombre", "habitacion"}


def test_cp10_edad_fuera_de_rango(api):
    cliente = api(URL_PACIENTES, PERSONAL)

    for edad in (0, 5, 500):
        respuesta = cliente.post("/pacientes", json={**NUEVO, "edad": edad})
        assert respuesta.status_code == 422


def test_cp11_paciente_duplicado(api):
    respuesta = api(URL_PACIENTES, PERSONAL).post(
        "/pacientes", json={**NUEVO, "nombre": "  juan   PEREZ "}
    )

    assert respuesta.status_code == 409
    assert "Ya existe" in respuesta.json()["mensaje"]


def test_cp14_actualizar_paciente(api):
    cliente = api(URL_PACIENTES, PERSONAL)

    respuesta = cliente.put("/pacientes/1", json={"habitacion": "C-10"})

    assert respuesta.status_code == 200
    assert cliente.get("/pacientes/1").json()["habitacion"] == "C-10"


def test_cp15_consultar_paciente_existente(api):
    respuesta = api(URL_PACIENTES, FARMACIA).get("/pacientes/1")

    assert respuesta.status_code == 200
    assert respuesta.json()["nombre"] == "Juan Pérez"


def test_cp16_paciente_inexistente_responde_404(api):
    respuesta = api(URL_PACIENTES, PERSONAL).get("/pacientes/999")

    assert respuesta.status_code == 404
    assert respuesta.json()["mensaje"] == "Paciente no encontrado."


def test_cp17_datos_invalidos_no_se_guardan(api):
    cliente = api(URL_PACIENTES, PERSONAL)
    antes = len(cliente.get("/pacientes").json()["pacientes"])

    for datos in ({"nombre": 123, "edad": "abc", "habitacion": None}, [], "texto"):
        assert cliente.post("/pacientes", json=datos).status_code == 422

    assert len(cliente.get("/pacientes").json()["pacientes"]) == antes


def test_cp18_eliminar_paciente(api):
    cliente = api(URL_PACIENTES, ADMINISTRADOR)

    assert cliente.delete("/pacientes/2").status_code == 200
    assert cliente.get("/pacientes/2").status_code == 404


def test_cp19_identificadores_unicos_despues_de_eliminar(api):
    cliente = api(URL_PACIENTES, ADMINISTRADOR)

    cliente.delete("/pacientes/2")
    nuevo = cliente.post("/pacientes", json=NUEVO).json()["paciente"]

    assert nuevo["id"] == 3


def test_busqueda_de_pacientes(api):
    respuesta = api(URL_PACIENTES, PERSONAL).get("/pacientes", params={"buscar": "maría"})

    nombres = [p["nombre"] for p in respuesta.json()["pacientes"]]
    assert nombres == ["María López"]


def test_cp37_acceso_sin_autenticacion(api):
    cliente = api(URL_PACIENTES)

    assert cliente.get("/pacientes").status_code == 401
    assert cliente.post("/pacientes", json=NUEVO).status_code == 401
    assert cliente.delete("/pacientes/1").status_code == 401


def test_cp36_acceso_segun_rol(api):
    assert api(URL_PACIENTES, FARMACIA).post("/pacientes", json=NUEVO).status_code == 403
    assert api(URL_PACIENTES, PERSONAL).delete("/pacientes/1").status_code == 403


def test_token_alterado_es_rechazado(api):
    cliente = api(URL_PACIENTES)
    respuesta = cliente.get("/pacientes", headers={"Authorization": "Bearer abc.def"})

    assert respuesta.status_code == 401
