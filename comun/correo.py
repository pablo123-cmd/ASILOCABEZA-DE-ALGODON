import asyncio
import smtplib
from email.message import EmailMessage

from comun import config


def _enviar_smtp(destinatario, asunto, cuerpo):
    mensaje = EmailMessage()
    mensaje["From"] = config.SMTP_REMITENTE
    mensaje["To"] = destinatario
    mensaje["Subject"] = asunto
    mensaje.set_content(cuerpo)

    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PUERTO, timeout=10) as smtp:
        smtp.starttls()
        if config.SMTP_USUARIO:
            smtp.login(config.SMTP_USUARIO, config.SMTP_CONTRASENA)
        smtp.send_message(mensaje)


async def enviar_correo(destinatario, asunto, cuerpo):
    """
    Envía un correo y devuelve el estado del envío. Un fallo en el
    envío no debe impedir la operación que lo originó, por eso los
    errores se devuelven como estado en lugar de lanzarse.
    """

    if not destinatario:
        return "No enviado: el paciente no tiene correo de familiar registrado"

    if not config.SMTP_HOST:
        return "Simulado: el servidor de correo (SMTP) no está configurado"

    try:
        await asyncio.to_thread(_enviar_smtp, destinatario, asunto, cuerpo)
        return "Enviado"
    except (OSError, smtplib.SMTPException) as error:
        return f"Error al enviar: {error}"
