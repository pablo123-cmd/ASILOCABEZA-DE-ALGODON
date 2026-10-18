"""
Prepara los servicios para las pruebas automáticas.

Cada prueba recarga los servicios, así empieza con los datos
iniciales. Las peticiones entre servicios no salen a la red: se
dirigen a las aplicaciones en memoria con httpx.ASGITransport.
"""

import importlib

import httpx
import pytest
from fastapi.testclient import TestClient

from comun import clientes, config
from comun.seguridad import crear_token

MODULOS = {
    "pacientes.main": config.URL_PACIENTES,
    "solicitudes.main": config.URL_SOLICITUDES,
    "medico.main": config.URL_MEDICO,
    "finanzas.main": config.URL_FINANZAS,
}


@pytest.fixture(autouse=True)
def servicios():
    aplicaciones = {}

    for nombre, url in MODULOS.items():
        modulo = importlib.reload(importlib.import_module(nombre))
        aplicaciones[url] = modulo.app

    clientes.configurar_montajes({
        url: httpx.ASGITransport(app=app) for url, app in aplicaciones.items()
    })

    yield aplicaciones

    clientes.configurar_montajes({})


@pytest.fixture
def api(servicios):
    """api(url_servicio, rol) -> cliente de pruebas autenticado con ese rol."""

    def crear(url, rol=None):
        encabezados = {}
        if rol:
            encabezados["Authorization"] = f"Bearer {crear_token('prueba', rol, 'Usuario de prueba')}"
        return TestClient(servicios[url], headers=encabezados)

    return crear


@pytest.fixture
def gateway(servicios):
    modulo = importlib.reload(importlib.import_module("gateway.main"))
    return TestClient(modulo.app, follow_redirects=False)
