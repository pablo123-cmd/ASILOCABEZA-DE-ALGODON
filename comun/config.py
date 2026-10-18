import os

# --------------------------------------------------
# DIRECCIONES DE LOS SERVICIOS
# --------------------------------------------------

URL_PACIENTES = os.getenv("URL_PACIENTES", "http://127.0.0.1:8000")
URL_SOLICITUDES = os.getenv("URL_SOLICITUDES", "http://127.0.0.1:8001")
URL_GATEWAY = os.getenv("URL_GATEWAY", "http://127.0.0.1:8002")
URL_MEDICO = os.getenv("URL_MEDICO", "http://127.0.0.1:8003")
URL_FINANZAS = os.getenv("URL_FINANZAS", "http://127.0.0.1:8004")

NOMBRES_SERVICIOS = {
    URL_PACIENTES: "pacientes",
    URL_SOLICITUDES: "solicitudes médicas",
    URL_MEDICO: "atención médica",
    URL_FINANZAS: "finanzas",
}

# --------------------------------------------------
# SEGURIDAD
# --------------------------------------------------

# La misma clave debe usarse en todos los servicios para que
# reconozcan la sesión creada por el menú principal.
CLAVE_SECRETA = os.getenv(
    "ASILO_CLAVE_SECRETA",
    "clave-de-desarrollo-cambiar-en-produccion"
)

DURACION_SESION_SEGUNDOS = 8 * 60 * 60

NOMBRE_COOKIE = "asilo_sesion"

# --------------------------------------------------
# REGLAS DE NEGOCIO
# --------------------------------------------------

EDAD_MINIMA = 60
EDAD_MAXIMA = 120

# --------------------------------------------------
# CORREO ELECTRÓNICO
# Si SMTP_HOST no está configurado, los correos se registran
# en el sistema como "simulados" en lugar de enviarse.
# --------------------------------------------------

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PUERTO = int(os.getenv("SMTP_PUERTO", "587"))
SMTP_USUARIO = os.getenv("SMTP_USUARIO", "")
SMTP_CONTRASENA = os.getenv("SMTP_CONTRASENA", "")
SMTP_REMITENTE = os.getenv(
    "SMTP_REMITENTE",
    SMTP_USUARIO or "notificaciones@asilo.local"
)
