"""Casos del plan SQA para el menú principal (secciones A, D, E y F)."""

from datetime import datetime, timedelta

import httpx
import pytest

from comun import clientes, config

CONTRASENA = "Asilo2026!"


def entrar(gateway, usuario, contrasena=CONTRASENA):
    gateway.cookies.clear()
    respuesta = gateway.post("/login", data={"usuario": usuario, "contrasena": contrasena})
    assert respuesta.status_code == 303, respuesta.text
    return respuesta


class Caido(httpx.AsyncBaseTransport):

    async def handle_async_request(self, request):
        raise httpx.ConnectError("Conexión rechazada", request=request)


# ---------- E. Seguridad ----------

def test_cp34_inicio_de_sesion_valido_muestra_modulos_del_rol(gateway):
    entrar(gateway, "laboratorio")

    menu = gateway.get("/").text

    assert "Laboratorio" in menu
    assert "/finanzas" not in menu
    assert "/usuarios" not in menu


def test_cp35_inicio_de_sesion_invalido(gateway):
    respuesta = gateway.post("/login", data={"usuario": "admin", "contrasena": "incorrecta"})

    assert respuesta.status_code == 401
    assert "Usuario o contraseña incorrectos" in respuesta.text
    assert gateway.get("/").status_code == 303


def test_cp36_acceso_segun_rol(gateway):
    entrar(gateway, "farmacia")

    respuesta = gateway.get("/finanzas")

    assert respuesta.status_code == 403
    assert "Acceso denegado" in respuesta.text


def test_cp37_sin_sesion_redirige_al_login(gateway):
    respuesta = gateway.get("/pacientes")

    assert respuesta.status_code == 303
    assert respuesta.headers["location"].startswith("/login")


def test_usuario_desactivado_pierde_acceso(gateway):
    entrar(gateway, "admin", "Admin2026!")
    gateway.post("/usuarios/2", data={"nombre": "Marta Gómez", "rol": "Personal del asilo", "activo": "no"})

    respuesta = gateway.post("/login", data={"usuario": "personal", "contrasena": CONTRASENA})

    assert respuesta.status_code == 403
    assert "desactivado" in respuesta.text


def test_rf02_crear_usuario_y_rol(gateway):
    entrar(gateway, "admin", "Admin2026!")

    corta = gateway.post("/usuarios/nuevo", data={
        "usuario": "nuevo", "nombre": "Nuevo", "rol": "Farmacia", "contrasena": "123"
    })
    creado = gateway.post("/usuarios/nuevo", data={
        "usuario": "nuevo", "nombre": "Nuevo", "rol": "Farmacia", "contrasena": "Segura2026"
    })

    assert corta.status_code == 422
    assert creado.status_code == 303
    entrar(gateway, "nuevo", "Segura2026")
    assert gateway.get("/farmacia").status_code == 200


def test_redireccion_despues_del_login_no_sale_del_sitio(gateway):
    respuesta = gateway.post("/login", data={
        "usuario": "admin", "contrasena": "Admin2026!", "siguiente": "//sitio-malicioso.com"
    })

    assert respuesta.headers["location"] == "/"


# ---------- B. Pacientes desde la interfaz ----------

def test_cp05_registro_con_datos_validos(gateway):
    entrar(gateway, "personal")

    respuesta = gateway.post("/pacientes/nuevo", data={
        "nombre": "Pedro Gómez", "edad": "70", "habitacion": "B-01"
    })

    assert respuesta.status_code == 303
    assert "Pedro Gómez" in gateway.get(respuesta.headers["location"]).text


def test_cp07_cp10_errores_se_muestran_en_el_formulario(gateway):
    entrar(gateway, "personal")

    respuesta = gateway.post("/pacientes/nuevo", data={"nombre": "Pedro", "edad": "500", "habitacion": ""})

    assert respuesta.status_code == 422
    assert "Debe ser menor o igual a 120" in respuesta.text
    assert "Este campo es obligatorio" in respuesta.text
    assert "Pedro" in respuesta.text  # conserva lo escrito


def test_cp12_html_en_el_nombre_no_se_interpreta(gateway):
    entrar(gateway, "personal")

    respuesta = gateway.post("/pacientes/nuevo", data={
        "nombre": "<script>alert(1)</script>", "edad": "70", "habitacion": "B-02"
    })
    pagina = gateway.get(respuesta.headers["location"]).text

    assert "<script>alert(1)</script>" not in pagina
    assert "&lt;script&gt;" in pagina


def test_cp13_buscar_y_editar_paciente(gateway):
    entrar(gateway, "personal")

    lista = gateway.get("/pacientes", params={"buscar": "lópez"}).text
    edicion = gateway.post("/pacientes/2/editar", data={
        "nombre": "María López", "edad": "81", "habitacion": "A-02"
    })

    assert "María López" in lista and "Juan Pérez" not in lista
    assert edicion.status_code == 303
    assert "81 años" in gateway.get("/pacientes/2").text


def test_edicion_rechaza_nombre_vacio(gateway):
    entrar(gateway, "personal")

    respuesta = gateway.post("/pacientes/2/editar", data={"nombre": " ", "edad": "81", "habitacion": "A-02"})

    assert respuesta.status_code == 422


# ---------- D. Integración ----------

def test_cp29_cp30_cp31_solicitud_desde_el_menu(gateway):
    entrar(gateway, "medico")

    formulario = gateway.get("/solicitudes/nueva")
    creada = gateway.post("/solicitudes/nueva", data={
        "paciente_id": "1", "especialidad": "Neurología", "motivo": "Control de memoria"
    })
    lista = gateway.get("/solicitudes").text

    assert formulario.status_code == 200
    assert formulario.text.count("<html") == 1  # una sola página, sin documentos anidados
    assert creada.status_code == 303
    assert "Control de memoria" in lista


def test_cp32_servicio_de_solicitudes_caido(gateway, servicios):
    entrar(gateway, "medico")
    clientes._montajes[config.URL_SOLICITUDES] = Caido()

    caida = gateway.get("/solicitudes")
    menu = gateway.get("/")
    pacientes = gateway.get("/pacientes")

    assert caida.status_code == 503
    assert "solicitudes médicas no está disponible" in caida.text
    assert menu.status_code == 200 and pacientes.status_code == 200


def test_cp33_servicio_de_pacientes_caido(gateway):
    entrar(gateway, "personal")
    clientes._montajes[config.URL_PACIENTES] = Caido()

    respuesta = gateway.get("/pacientes")

    assert respuesta.status_code == 503
    assert "Volver al menú principal" in respuesta.text


# ---------- Flujo completo ----------

def test_flujo_completo_de_atencion_y_cobro(gateway):
    horario = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M")

    entrar(gateway, "medico")
    gateway.post("/solicitudes/nueva", data={
        "paciente_id": "1", "especialidad": "Cardiología", "motivo": "Dolor torácico", "enfermero_id": "1"
    })

    entrar(gateway, "fundacion")
    assert gateway.post("/solicitudes/3/asignacion", data={
        "medico_id": "2", "horario": horario
    }).status_code == 303

    entrar(gateway, "especialista")
    assert gateway.post("/visitas/nueva", data={
        "solicitud_id": "3", "diagnostico": "Angina estable"
    }).headers["location"].startswith("/visitas/1")
    gateway.post("/visitas/1/examenes", data={"tipo_examen_id": "5"})
    gateway.post("/visitas/1/recetas", data={
        "medicamento_id": "3", "cantidad": "10", "indicaciones": "Cada 8 horas", "duracion": "3 días"
    })

    entrar(gateway, "laboratorio")
    assert gateway.post("/laboratorio/1/resultado", data={"resultado": "Ritmo sinusal"}).status_code == 303

    entrar(gateway, "farmacia")
    assert gateway.post("/farmacia/1/entregar").status_code == 303

    entrar(gateway, "finanzas")
    cuenta = gateway.get("/finanzas/cuentas/1").text
    # Consulta 250, ECG 150, medicamento 5: total 405 con 25 % de descuento = 303.75
    assert "Q 303.75" in cuenta
    assert gateway.post("/finanzas/cuentas/1/cobro", data={"visita_id": "1", "monto": "303.75"}).status_code == 303
    assert "Pagada" in gateway.get("/finanzas/cuentas/1").text

    entrar(gateway, "medico")
    historial = gateway.get("/pacientes/1/ficha").text
    correos = gateway.get("/notificaciones").text
    assert "Angina estable" in historial and "Ritmo sinusal" in historial
    assert "Cita asignada para Juan Pérez" in correos


# ---------- Todas las pantallas cargan ----------

PANTALLAS = [
    "/", "/pacientes", "/pacientes/nuevo", "/pacientes/1", "/pacientes/1/editar",
    "/pacientes/1/ficha", "/solicitudes", "/solicitudes/nueva", "/solicitudes/1",
    "/solicitudes/2", "/visitas", "/visitas/nueva?solicitud_id=2", "/laboratorio",
    "/farmacia", "/catalogos", "/catalogos/especialidades", "/catalogos/medicos",
    "/catalogos/enfermeros", "/catalogos/tipos-examen", "/catalogos/medicamentos",
    "/catalogos/medicos/1", "/finanzas", "/finanzas/cuentas", "/finanzas/cuentas/1",
    "/finanzas/donaciones", "/finanzas/cuotas", "/finanzas/cobros", "/finanzas/gastos",
    "/finanzas/pagos-fundacion", "/reportes", "/reportes/costos-por-cita",
    "/reportes/analisis-medico?paciente_id=1", "/reportes/cobros",
    "/reportes/pagos-fundacion", "/reportes/entradas", "/reportes/examenes",
    "/reportes/medicamentos", "/notificaciones", "/usuarios", "/usuarios/nuevo", "/usuarios/1",
]


@pytest.mark.parametrize("ruta", PANTALLAS)
def test_cp01_cp02_pantallas_cargan(gateway, ruta):
    entrar(gateway, "admin", "Admin2026!")

    respuesta = gateway.get(ruta)

    assert respuesta.status_code == 200, respuesta.text[:500]
    assert 'name="viewport"' in respuesta.text


def test_catalogo_agregar_y_editar(gateway):
    entrar(gateway, "fundacion")

    agregado = gateway.post("/catalogos/especialidades", data={"nombre": "Geriatría", "precio_consulta": "180"})
    duplicado = gateway.post("/catalogos/especialidades", data={"nombre": "geriatría", "precio_consulta": "1"})
    editado = gateway.post("/catalogos/especialidades/7", data={"nombre": "Geriatría", "precio_consulta": "190"})

    assert agregado.status_code == 303
    assert duplicado.status_code == 422 and "Ya existe" in duplicado.text
    assert editado.status_code == 303
    assert "Q 190.00" in gateway.get("/catalogos/especialidades").text


def test_movimientos_financieros_desde_la_interfaz(gateway):
    entrar(gateway, "finanzas")

    donacion = gateway.post("/finanzas/donaciones", data={
        "tipo_donante": "Gobierno", "donante": "Municipalidad", "monto": "800"
    })
    invalida = gateway.post("/finanzas/gastos", data={"categoria": "Luz", "descripcion": "x", "monto": "-5"})

    assert donacion.status_code == 303
    assert invalida.status_code == 422
    assert "Municipalidad" in gateway.get("/reportes/entradas").text


def test_reporte_rango_de_fechas_invalido(gateway):
    entrar(gateway, "finanzas")

    assert gateway.get("/reportes/entradas?desde=2026-12-01&hasta=2026-01-01").status_code == 400
    assert gateway.get("/reportes/entradas?desde=no-es-fecha").status_code == 400


def test_pagina_inexistente(gateway):
    entrar(gateway, "admin", "Admin2026!")

    respuesta = gateway.get("/no-existe")

    assert respuesta.status_code == 404
    assert "Página no encontrada" in respuesta.text
