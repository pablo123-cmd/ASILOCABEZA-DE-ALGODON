import base64
import hashlib
import hmac
import json
import os
import time

from fastapi import HTTPException, Request

from comun.config import (
    CLAVE_SECRETA,
    DURACION_SESION_SEGUNDOS,
    NOMBRE_COOKIE
)

# --------------------------------------------------
# ROLES DEL SISTEMA
# --------------------------------------------------

ADMINISTRADOR = "Administrador"
PERSONAL = "Personal del asilo"
MEDICO_GENERAL = "Médico general"
ESPECIALISTA = "Médico especialista"
ENFERMERO = "Enfermero(a)"
FUNDACION = "Fundación"
LABORATORIO = "Laboratorio"
FARMACIA = "Farmacia"
FINANCIERO = "Encargado financiero"

# Rol que usan los servicios para consultarse entre sí.
SERVICIO = "Servicio interno"

ROLES = [
    ADMINISTRADOR,
    PERSONAL,
    MEDICO_GENERAL,
    ESPECIALISTA,
    ENFERMERO,
    FUNDACION,
    LABORATORIO,
    FARMACIA,
    FINANCIERO,
]

MEDICOS = (MEDICO_GENERAL, ESPECIALISTA)

# --------------------------------------------------
# PERMISOS POR OPERACIÓN
# El administrador y los servicios internos tienen acceso a todo.
# --------------------------------------------------

LEER_PACIENTES = (
    PERSONAL, *MEDICOS, ENFERMERO, FUNDACION,
    LABORATORIO, FARMACIA, FINANCIERO
)
EDITAR_PACIENTES = (PERSONAL,)

LEER_FICHA = (*MEDICOS, ENFERMERO)
EDITAR_FICHA = MEDICOS

LEER_SOLICITUDES = (*MEDICOS, ENFERMERO, FUNDACION)
CREAR_SOLICITUDES = (MEDICO_GENERAL,)
ASIGNAR_ENFERMERO = (MEDICO_GENERAL,)
ASIGNAR_MEDICO = (FUNDACION,)
CANCELAR_SOLICITUDES = (MEDICO_GENERAL, FUNDACION)

LEER_CATALOGOS = (
    PERSONAL, *MEDICOS, ENFERMERO, FUNDACION,
    LABORATORIO, FARMACIA, FINANCIERO
)
EDITAR_CATALOGOS = (FUNDACION,)
EDITAR_ENFERMEROS = (PERSONAL,)

LEER_VISITAS = (*MEDICOS, ENFERMERO, LABORATORIO, FARMACIA)
REGISTRAR_VISITAS = MEDICOS

LEER_LABORATORIO = (*MEDICOS, LABORATORIO)
REGISTRAR_RESULTADOS = (LABORATORIO,)

LEER_FARMACIA = (*MEDICOS, FARMACIA)
ENTREGAR_MEDICAMENTOS = (FARMACIA,)

LEER_COSTOS = (FINANCIERO, FUNDACION)
FINANZAS = (FINANCIERO,)

VER_NOTIFICACIONES = (MEDICO_GENERAL,)


def tiene_permiso(rol, roles_permitidos):
    return rol in (ADMINISTRADOR, SERVICIO) or rol in roles_permitidos


# --------------------------------------------------
# CONTRASEÑAS
# --------------------------------------------------

ITERACIONES = 120_000


def cifrar_contrasena(contrasena):
    sal = os.urandom(16)
    resumen = hashlib.pbkdf2_hmac(
        "sha256", contrasena.encode(), sal, ITERACIONES
    )
    return f"{sal.hex()}${resumen.hex()}"


def verificar_contrasena(contrasena, cifrada):
    try:
        sal_hex, resumen_hex = cifrada.split("$")
    except ValueError:
        return False

    resumen = hashlib.pbkdf2_hmac(
        "sha256", contrasena.encode(), bytes.fromhex(sal_hex), ITERACIONES
    )
    return hmac.compare_digest(resumen.hex(), resumen_hex)


# --------------------------------------------------
# TOKENS DE SESIÓN
# Formato: datos_en_base64.firma_en_base64
# La firma usa la clave secreta compartida por los servicios.
# --------------------------------------------------

def _b64(datos):
    return base64.urlsafe_b64encode(datos).rstrip(b"=").decode()


def _desde_b64(texto):
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


def _firmar(contenido):
    return hmac.new(
        CLAVE_SECRETA.encode(), contenido.encode(), hashlib.sha256
    ).digest()


def crear_token(usuario, rol, nombre):
    datos = {
        "usuario": usuario,
        "rol": rol,
        "nombre": nombre,
        "exp": int(time.time()) + DURACION_SESION_SEGUNDOS
    }
    contenido = _b64(json.dumps(datos).encode())
    return f"{contenido}.{_b64(_firmar(contenido))}"


def verificar_token(token):
    """Devuelve los datos del token o None si es inválido o expiró."""

    try:
        contenido, firma = token.split(".")
        if not hmac.compare_digest(_desde_b64(firma), _firmar(contenido)):
            return None

        datos = json.loads(_desde_b64(contenido))
    except (ValueError, TypeError):
        return None

    if datos.get("exp", 0) < time.time():
        return None

    return datos


def token_servicio():
    return crear_token("servicio", SERVICIO, "Servicio interno")


# --------------------------------------------------
# DEPENDENCIA PARA PROTEGER LOS ENDPOINTS
# Uso: usuario: dict = Depends(requiere(LEER_PACIENTES))
# --------------------------------------------------

def token_de_peticion(request: Request):
    encabezado = request.headers.get("Authorization", "")

    if encabezado.startswith("Bearer "):
        return encabezado[len("Bearer "):]

    return request.cookies.get(NOMBRE_COOKIE)


def requiere(roles_permitidos):

    def dependencia(request: Request):
        token = token_de_peticion(request)
        usuario = verificar_token(token) if token else None

        if usuario is None:
            raise HTTPException(
                status_code=401,
                detail="Debe iniciar sesión para acceder a esta información."
            )

        if not tiene_permiso(usuario["rol"], roles_permitidos):
            raise HTTPException(
                status_code=403,
                detail="Su rol no tiene permiso para realizar esta operación."
            )

        return usuario

    return dependencia
