from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from comun.clientes import ServicioNoDisponible, pedir
from comun.config import (
    DURACION_SESION_SEGUNDOS, EDAD_MAXIMA, EDAD_MINIMA, NOMBRE_COOKIE,
    URL_FINANZAS, URL_MEDICO, URL_PACIENTES, URL_SOLICITUDES
)
from comun.modelos import normalizar
from comun.repositorio import RepositorioMemoria
from comun import seguridad as seg
from comun.seguridad import (
    ADMINISTRADOR, cifrar_contrasena, crear_token, tiene_permiso,
    verificar_contrasena, verificar_token
)

# ==================================================
# CREACIÓN DE LA APLICACIÓN
# ==================================================

app = FastAPI(
    title="Sistema Asilo Cabeza de Algodón",
    description="Menú principal (gateway): interfaz del usuario, inicio de sesión y reportes",
    version="2.0"
)

CARPETA = Path(__file__).parent

app.mount("/estatico", StaticFiles(directory=CARPETA / "estatico"), name="estatico")

plantillas = Jinja2Templates(directory=CARPETA / "plantillas")


def _formato_fecha(valor):
    if not valor:
        return "—"
    texto = str(valor)
    try:
        if "T" in texto or " " in texto:
            return datetime.fromisoformat(texto).strftime("%d/%m/%Y %H:%M")
        return date.fromisoformat(texto).strftime("%d/%m/%Y")
    except ValueError:
        return texto


def _formato_moneda(valor):
    return "—" if valor is None else f"Q {valor:,.2f}"


def _opciones(registros, valor="id", texto="nombre"):
    """Pares (valor, texto) para un campo de selección."""
    return [(r[valor], r[texto]) for r in registros]


plantillas.env.filters["fecha"] = _formato_fecha
plantillas.env.filters["q"] = _formato_moneda
plantillas.env.globals.update(
    opciones=_opciones, EDAD_MINIMA=EDAD_MINIMA, EDAD_MAXIMA=EDAD_MAXIMA
)

# ==================================================
# USUARIOS (en memoria hasta conectar la base de datos)
# Las contraseñas se guardan cifradas, nunca en texto plano.
# ==================================================

usuarios = RepositorioMemoria([
    {"usuario": usuario, "nombre": nombre, "rol": rol, "activo": True,
     "contrasena": cifrar_contrasena(contrasena)}
    for usuario, nombre, rol, contrasena in [
        ("admin", "Administrador del sistema", seg.ADMINISTRADOR, "Admin2026!"),
        ("personal", "Marta Gómez", seg.PERSONAL, "Asilo2026!"),
        ("medico", "Dr. Roberto Castillo", seg.MEDICO_GENERAL, "Asilo2026!"),
        ("especialista", "Dra. Ana Ruiz", seg.ESPECIALISTA, "Asilo2026!"),
        ("enfermero", "Rosa Hernández", seg.ENFERMERO, "Asilo2026!"),
        ("fundacion", "Coordinación de la Fundación", seg.FUNDACION, "Asilo2026!"),
        ("laboratorio", "Laboratorio Clínico", seg.LABORATORIO, "Asilo2026!"),
        ("farmacia", "Farmacia de la Fundación", seg.FARMACIA, "Asilo2026!"),
        ("finanzas", "Lucía Ramírez", seg.FINANCIERO, "Asilo2026!"),
    ]
])

LONGITUD_MINIMA_CONTRASENA = 8

# ==================================================
# MÓDULOS DEL MENÚ
# Cada usuario solo ve los módulos que su rol permite.
# ==================================================

MODULOS = [
    {"titulo": "Pacientes", "icono": "👴", "ruta": "/pacientes", "roles": seg.LEER_PACIENTES,
     "descripcion": "Registrar, buscar y actualizar los internos del asilo."},
    {"titulo": "Solicitudes médicas", "icono": "📋", "ruta": "/solicitudes",
     "roles": seg.LEER_SOLICITUDES,
     "descripcion": "Referencias a especialistas, enfermero, médico y horario."},
    {"titulo": "Atención médica", "icono": "🩺", "ruta": "/visitas", "roles": seg.LEER_VISITAS,
     "descripcion": "Visitas médicas, diagnósticos, exámenes y medicamentos."},
    {"titulo": "Laboratorio", "icono": "🧪", "ruta": "/laboratorio",
     "roles": seg.LEER_LABORATORIO,
     "descripcion": "Exámenes solicitados y registro de resultados."},
    {"titulo": "Farmacia", "icono": "💊", "ruta": "/farmacia", "roles": seg.LEER_FARMACIA,
     "descripcion": "Entrega de medicamentos indicados en las visitas."},
    {"titulo": "Médicos y catálogos", "icono": "🏥", "ruta": "/catalogos",
     "roles": seg.LEER_CATALOGOS,
     "descripcion": "Médicos, especialidades, enfermeros, exámenes, medicamentos y precios."},
    {"titulo": "Finanzas", "icono": "💰", "ruta": "/finanzas", "roles": seg.FINANZAS,
     "descripcion": "Cuentas, cobros, cuotas, donaciones, gastos y pagos a la fundación."},
    {"titulo": "Reportes", "icono": "📊", "ruta": "/reportes",
     "roles": (*seg.FINANZAS, *seg.MEDICOS, seg.LABORATORIO, seg.FARMACIA),
     "descripcion": "Informes médicos y financieros por paciente y por fecha."},
    {"titulo": "Correos a familiares", "icono": "✉️", "ruta": "/notificaciones",
     "roles": seg.VER_NOTIFICACIONES,
     "descripcion": "Avisos enviados a los familiares sobre las solicitudes."},
    {"titulo": "Usuarios", "icono": "🔐", "ruta": "/usuarios", "roles": (ADMINISTRADOR,),
     "descripcion": "Cuentas de acceso y roles del personal."},
]

# ==================================================
# SESIÓN, PERMISOS Y ERRORES
# ==================================================


class RedirigirLogin(Exception):
    pass


class ErrorPagina(Exception):

    def __init__(self, titulo, mensaje, codigo=400):
        super().__init__(mensaje)
        self.titulo = titulo
        self.mensaje = mensaje
        self.codigo = codigo


def sin_permiso(mensaje="Su rol no tiene permiso para usar este módulo."):
    return ErrorPagina("Acceso denegado", mensaje, 403)


def con_permiso(roles):
    """Dependencia: exige sesión iniciada y uno de los roles indicados."""

    def dependencia(request: Request):
        token = request.cookies.get(NOMBRE_COOKIE)
        usuario = verificar_token(token) if token else None

        if usuario is None:
            raise RedirigirLogin()

        # Un usuario desactivado pierde el acceso aunque su sesión
        # no haya expirado.
        registrado = usuarios.listar(lambda u: u["usuario"] == usuario["usuario"])
        if not registrado or not registrado[0]["activo"] or registrado[0]["rol"] != usuario["rol"]:
            raise RedirigirLogin()

        if not tiene_permiso(usuario["rol"], roles):
            raise sin_permiso()

        request.state.token = token
        request.state.usuario = usuario
        return usuario

    return dependencia


sesion = con_permiso(seg.ROLES)


@app.exception_handler(RedirigirLogin)
async def ir_a_login(request: Request, exc: RedirigirLogin):
    respuesta = RedirectResponse(f"/login?siguiente={quote(request.url.path)}", status_code=303)
    respuesta.delete_cookie(NOMBRE_COOKIE)
    return respuesta


@app.exception_handler(ErrorPagina)
async def mostrar_error(request: Request, exc: ErrorPagina):
    return pagina(request, "error.html", exc.codigo, titulo=exc.titulo, mensaje=exc.mensaje)


@app.exception_handler(ServicioNoDisponible)
async def servicio_caido(request: Request, exc: ServicioNoDisponible):
    return pagina(
        request, "error.html", 503,
        titulo="Servicio no disponible",
        mensaje=(
            f"El servicio de {exc.servicio} no está disponible en este momento. "
            "Puede seguir usando los demás módulos del menú; intente de nuevo "
            "en unos minutos y, si el problema continúa, avise al administrador."
        )
    )


@app.exception_handler(404)
async def no_existe(request: Request, exc):
    return pagina(request, "error.html", 404, titulo="Página no encontrada",
                  mensaje="La dirección solicitada no existe.")


def pagina(request, plantilla, codigo=200, **contexto):
    usuario = getattr(request.state, "usuario", None)
    rol = usuario["rol"] if usuario else None

    return plantillas.TemplateResponse(
        request,
        plantilla,
        {
            "usuario": usuario,
            "modulos": [m for m in MODULOS if rol and tiene_permiso(rol, m["roles"])],
            "puede": lambda roles: bool(rol) and tiene_permiso(rol, roles),
            "seg": seg,
            "ok": request.query_params.get("ok", ""),
            **contexto
        },
        status_code=codigo
    )


def redirigir(ruta, mensaje=""):
    if mensaje:
        separador = "&" if "?" in ruta else "?"
        ruta = f"{ruta}{separador}ok={quote(mensaje)}"
    return RedirectResponse(ruta, status_code=303)


# ==================================================
# COMUNICACIÓN CON LOS MICROSERVICIOS
# Las peticiones llevan el token del usuario, así cada servicio
# aplica también los permisos de su rol.
# ==================================================

async def api(request, metodo, url, ruta, **opciones):
    respuesta = await pedir(metodo, url, ruta, token=request.state.token, **opciones)

    if respuesta.status_code == 401:
        raise RedirigirLogin()

    if respuesta.status_code == 403:
        raise sin_permiso(respuesta.json().get("mensaje", "Acceso denegado."))

    if respuesta.status_code >= 500:
        raise ErrorPagina(
            "Error del servicio",
            respuesta.json().get("mensaje", "El servicio tuvo un problema; intente de nuevo."),
            503
        )

    return respuesta


async def datos(request, url, ruta, **parametros):
    """GET a un servicio; muestra una página de error si falla."""

    parametros = {k: v for k, v in parametros.items() if v not in (None, "")}
    respuesta = await api(request, "GET", url, ruta, params=parametros)

    if respuesta.status_code == 404:
        raise ErrorPagina("No encontrado", respuesta.json()["mensaje"], 404)

    if respuesta.status_code >= 400:
        raise ErrorPagina("Datos inválidos", _errores(respuesta)[0])

    return respuesta.json()


def _errores(respuesta):
    """(mensaje general, {campo: mensaje}) a partir de una respuesta de error."""

    try:
        cuerpo = respuesta.json()
    except ValueError:
        cuerpo = {}

    errores = {e["campo"]: e["mensaje"] for e in cuerpo.get("errores", [])}
    mensaje = cuerpo.get("mensaje", "No se pudo completar la operación.")

    if errores and mensaje == "Los datos enviados no son válidos.":
        mensaje = "Revise los campos marcados en rojo."

    return mensaje, errores


async def formulario(request, *opcionales):
    """
    Lee un formulario HTML. Los campos vacíos se omiten para que el
    servicio los reporte como obligatorios; los nombrados en
    `opcionales` se envían vacíos para poder borrar su contenido.
    """

    form = await request.form()
    valores = {}

    for campo, valor in form.items():
        if valor != "" or campo in opcionales:
            valores[campo] = valor

    return valores


def _parametros_fecha(request):
    return {
        "desde": request.query_params.get("desde", ""),
        "hasta": request.query_params.get("hasta", "")
    }


async def _pacientes(request):
    return (await datos(request, URL_PACIENTES, "/pacientes"))["pacientes"]


async def _nombres_pacientes(request):
    return {p["id"]: p["nombre"] for p in await _pacientes(request)}


# ==================================================
# INICIO DE SESIÓN
# ==================================================

def _siguiente_seguro(ruta):
    """Evita redirigir a otro sitio después de iniciar sesión."""

    if ruta.startswith("/") and not ruta.startswith("//") and ruta != "/login":
        return ruta
    return "/"


@app.get("/login", response_class=HTMLResponse)
def ver_login(request: Request, siguiente: str = "/"):
    return pagina(request, "login.html", siguiente=_siguiente_seguro(siguiente))


@app.post("/login", response_class=HTMLResponse)
async def iniciar_sesion(request: Request):

    form = await request.form()
    nombre_usuario = normalizar(str(form.get("usuario", "")))
    contrasena = str(form.get("contrasena", ""))
    siguiente = _siguiente_seguro(str(form.get("siguiente", "/")))

    encontrados = usuarios.listar(lambda u: u["usuario"] == nombre_usuario)
    usuario = encontrados[0] if encontrados else None

    if usuario is None or not verificar_contrasena(contrasena, usuario["contrasena"]):
        return pagina(
            request, "login.html", 401, siguiente=siguiente, usuario_escrito=nombre_usuario,
            error="Usuario o contraseña incorrectos."
        )

    if not usuario["activo"]:
        return pagina(
            request, "login.html", 403, siguiente=siguiente, usuario_escrito=nombre_usuario,
            error="Su usuario está desactivado. Comuníquese con el administrador."
        )

    respuesta = RedirectResponse(siguiente, status_code=303)
    respuesta.set_cookie(
        NOMBRE_COOKIE,
        crear_token(usuario["usuario"], usuario["rol"], usuario["nombre"]),
        max_age=DURACION_SESION_SEGUNDOS,
        httponly=True,
        samesite="lax"
    )
    return respuesta


@app.get("/salir")
def cerrar_sesion():
    respuesta = RedirectResponse("/login", status_code=303)
    respuesta.delete_cookie(NOMBRE_COOKIE)
    return respuesta


# ==================================================
# MENÚ PRINCIPAL
# ==================================================

@app.get("/", response_class=HTMLResponse)
def inicio(request: Request, usuario: dict = Depends(sesion)):
    return pagina(request, "menu.html")


# ==================================================
# PACIENTES
# ==================================================

CAMPOS_PACIENTE_OPCIONALES = (
    "motivo_ingreso", "familiar_nombre", "familiar_telefono", "familiar_correo"
)


@app.get("/pacientes", response_class=HTMLResponse)
async def lista_pacientes(
    request: Request, buscar: str = "",
    usuario: dict = Depends(con_permiso(seg.LEER_PACIENTES))
):
    respuesta = await datos(request, URL_PACIENTES, "/pacientes", buscar=buscar)
    return pagina(request, "pacientes_lista.html", pacientes=respuesta["pacientes"], buscar=buscar)


@app.get("/pacientes/nuevo", response_class=HTMLResponse)
def nuevo_paciente(request: Request, usuario: dict = Depends(con_permiso(seg.EDITAR_PACIENTES))):
    return pagina(request, "paciente_form.html", paciente={}, errores={})


@app.post("/pacientes/nuevo", response_class=HTMLResponse)
async def registrar_paciente(
    request: Request, usuario: dict = Depends(con_permiso(seg.EDITAR_PACIENTES))
):
    valores = await formulario(request)
    respuesta = await api(request, "POST", URL_PACIENTES, "/pacientes", json=valores)

    if respuesta.status_code == 201:
        paciente = respuesta.json()["paciente"]
        return redirigir(f"/pacientes/{paciente['id']}", "Paciente registrado correctamente.")

    mensaje, errores = _errores(respuesta)
    return pagina(request, "paciente_form.html", 422, paciente=valores, errores=errores, error=mensaje)


@app.get("/pacientes/{paciente_id}", response_class=HTMLResponse)
async def ver_paciente(
    request: Request, paciente_id: int,
    usuario: dict = Depends(con_permiso(seg.LEER_PACIENTES))
):
    paciente = await datos(request, URL_PACIENTES, f"/pacientes/{paciente_id}")
    solicitudes = []

    if tiene_permiso(usuario["rol"], seg.LEER_SOLICITUDES):
        respuesta = await datos(
            request, URL_SOLICITUDES, "/solicitudes", paciente_id=paciente_id
        )
        solicitudes = respuesta["solicitudes"]

    return pagina(request, "paciente_detalle.html", paciente=paciente, solicitudes=solicitudes)


@app.get("/pacientes/{paciente_id}/editar", response_class=HTMLResponse)
async def editar_paciente(
    request: Request, paciente_id: int,
    usuario: dict = Depends(con_permiso(seg.EDITAR_PACIENTES))
):
    paciente = await datos(request, URL_PACIENTES, f"/pacientes/{paciente_id}")
    return pagina(request, "paciente_form.html", paciente=paciente, errores={})


@app.post("/pacientes/{paciente_id}/editar", response_class=HTMLResponse)
async def guardar_paciente(
    request: Request, paciente_id: int,
    usuario: dict = Depends(con_permiso(seg.EDITAR_PACIENTES))
):
    valores = await formulario(request, *CAMPOS_PACIENTE_OPCIONALES)

    # En una edición, un campo obligatorio vacío debe rechazarse,
    # no ignorarse: se envía vacío para que el servicio lo valide.
    for campo in ("nombre", "edad", "habitacion"):
        valores.setdefault(campo, "")

    respuesta = await api(
        request, "PUT", URL_PACIENTES, f"/pacientes/{paciente_id}", json=valores
    )

    if respuesta.status_code == 200:
        return redirigir(f"/pacientes/{paciente_id}", "Datos del paciente actualizados.")

    mensaje, errores = _errores(respuesta)
    return pagina(
        request, "paciente_form.html", 422,
        paciente={**valores, "id": paciente_id}, errores=errores, error=mensaje
    )


# ==================================================
# FICHA E HISTORIAL MÉDICO
# ==================================================

@app.get("/pacientes/{paciente_id}/ficha", response_class=HTMLResponse)
async def ver_ficha(
    request: Request, paciente_id: int,
    usuario: dict = Depends(con_permiso(seg.LEER_FICHA))
):
    ficha = await datos(request, URL_MEDICO, f"/fichas/{paciente_id}")
    return pagina(request, "ficha.html", **ficha, errores={})


@app.post("/pacientes/{paciente_id}/ficha", response_class=HTMLResponse)
async def guardar_ficha(
    request: Request, paciente_id: int,
    usuario: dict = Depends(con_permiso(seg.EDITAR_FICHA))
):
    form = await request.form()
    valores = dict(form)
    respuesta = await api(request, "PUT", URL_MEDICO, f"/fichas/{paciente_id}", json=valores)

    if respuesta.status_code == 200:
        return redirigir(f"/pacientes/{paciente_id}/ficha", "Ficha médica guardada.")

    ficha = await datos(request, URL_MEDICO, f"/fichas/{paciente_id}")
    mensaje, errores = _errores(respuesta)
    ficha["ficha"].update(valores)
    return pagina(request, "ficha.html", 422, **ficha, errores=errores, error=mensaje)


# ==================================================
# SOLICITUDES MÉDICAS
# ==================================================

ESTADOS_SOLICITUD = ["Pendiente", "Asignada", "Atendida", "Cancelada"]


@app.get("/solicitudes", response_class=HTMLResponse)
async def lista_solicitudes(
    request: Request, estado: str = "",
    usuario: dict = Depends(con_permiso(seg.LEER_SOLICITUDES))
):
    if estado and estado not in ESTADOS_SOLICITUD:
        estado = ""

    respuesta = await datos(request, URL_SOLICITUDES, "/solicitudes", estado=estado)
    return pagina(
        request, "solicitudes_lista.html",
        solicitudes=respuesta["solicitudes"], estado=estado, estados=ESTADOS_SOLICITUD
    )


async def _form_solicitud(request, valores, errores, codigo=200, error=""):
    return pagina(
        request, "solicitud_form.html", codigo,
        valores=valores, errores=errores, error=error,
        pacientes=await _pacientes(request),
        especialidades=await datos(request, URL_MEDICO, "/especialidades"),
        enfermeros=await datos(request, URL_MEDICO, "/enfermeros")
    )


@app.get("/solicitudes/nueva", response_class=HTMLResponse)
async def nueva_solicitud(
    request: Request, paciente_id: str = "",
    usuario: dict = Depends(con_permiso(seg.CREAR_SOLICITUDES))
):
    return await _form_solicitud(request, {"paciente_id": paciente_id}, {})


@app.post("/solicitudes/nueva", response_class=HTMLResponse)
async def crear_solicitud(
    request: Request, usuario: dict = Depends(con_permiso(seg.CREAR_SOLICITUDES))
):
    valores = await formulario(request)
    respuesta = await api(request, "POST", URL_SOLICITUDES, "/solicitudes", json=valores)

    if respuesta.status_code == 201:
        solicitud = respuesta.json()["solicitud"]
        return redirigir(
            f"/solicitudes/{solicitud['id']}",
            "Solicitud creada correctamente y aviso enviado al familiar."
        )

    mensaje, errores = _errores(respuesta)
    return await _form_solicitud(request, valores, errores, 422, mensaje)


async def _detalle_solicitud(request, solicitud_id, codigo=200, error="", errores=None):
    solicitud = await datos(request, URL_SOLICITUDES, f"/solicitudes/{solicitud_id}")
    rol = request.state.usuario["rol"]
    medicos, enfermeros = [], []

    if solicitud["estado"] in ("Pendiente", "Asignada"):
        if tiene_permiso(rol, seg.ASIGNAR_MEDICO):
            medicos = [
                m for m in await datos(request, URL_MEDICO, "/medicos")
                if m["especialidad_id"] == solicitud["especialidad_id"]
            ]
        if tiene_permiso(rol, (*seg.ASIGNAR_MEDICO, *seg.ASIGNAR_ENFERMERO)):
            enfermeros = await datos(request, URL_MEDICO, "/enfermeros")

    return pagina(
        request, "solicitud_detalle.html", codigo,
        solicitud=solicitud, medicos=medicos, enfermeros=enfermeros,
        error=error, errores=errores or {}
    )


@app.get("/solicitudes/{solicitud_id}", response_class=HTMLResponse)
async def ver_solicitud(
    request: Request, solicitud_id: int,
    usuario: dict = Depends(con_permiso(seg.LEER_SOLICITUDES))
):
    return await _detalle_solicitud(request, solicitud_id)


async def _accion_solicitud(request, solicitud_id, ruta, valores, mensaje_exito):
    respuesta = await api(
        request, "PUT", URL_SOLICITUDES, f"/solicitudes/{solicitud_id}{ruta}", json=valores
    )

    if respuesta.status_code == 200:
        return redirigir(f"/solicitudes/{solicitud_id}", mensaje_exito)

    mensaje, errores = _errores(respuesta)
    return await _detalle_solicitud(request, solicitud_id, 422, mensaje, errores)


@app.post("/solicitudes/{solicitud_id}/enfermero", response_class=HTMLResponse)
async def asignar_enfermero(
    request: Request, solicitud_id: int,
    usuario: dict = Depends(con_permiso(seg.ASIGNAR_ENFERMERO))
):
    return await _accion_solicitud(
        request, solicitud_id, "/enfermero", await formulario(request),
        "Enfermero(a) asignado correctamente."
    )


@app.post("/solicitudes/{solicitud_id}/asignacion", response_class=HTMLResponse)
async def asignar_medico(
    request: Request, solicitud_id: int,
    usuario: dict = Depends(con_permiso(seg.ASIGNAR_MEDICO))
):
    return await _accion_solicitud(
        request, solicitud_id, "/asignacion", await formulario(request),
        "Médico y horario asignados. Se avisó al familiar."
    )


@app.post("/solicitudes/{solicitud_id}/cancelar", response_class=HTMLResponse)
async def cancelar_solicitud(
    request: Request, solicitud_id: int,
    usuario: dict = Depends(con_permiso(seg.CANCELAR_SOLICITUDES))
):
    return await _accion_solicitud(
        request, solicitud_id, "/estado", {"estado": "Cancelada"}, "Solicitud cancelada."
    )


# ==================================================
# ATENCIÓN MÉDICA (VISITAS)
# ==================================================

@app.get("/visitas", response_class=HTMLResponse)
async def lista_visitas(
    request: Request, usuario: dict = Depends(con_permiso(seg.LEER_VISITAS))
):
    visitas = await datos(request, URL_MEDICO, "/visitas")
    por_atender = []

    if tiene_permiso(usuario["rol"], seg.REGISTRAR_VISITAS):
        respuesta = await datos(request, URL_SOLICITUDES, "/solicitudes", estado="Asignada")
        por_atender = sorted(respuesta["solicitudes"], key=lambda s: s["horario"] or "")

    nombres = await _nombres_pacientes(request)
    return pagina(request, "visitas_lista.html", visitas=visitas,
                  por_atender=por_atender, nombres=nombres)


@app.get("/visitas/nueva", response_class=HTMLResponse)
async def nueva_visita(
    request: Request, solicitud_id: int,
    usuario: dict = Depends(con_permiso(seg.REGISTRAR_VISITAS))
):
    solicitud = await datos(request, URL_SOLICITUDES, f"/solicitudes/{solicitud_id}")
    return pagina(request, "visita_form.html", solicitud=solicitud, valores={}, errores={})


@app.post("/visitas/nueva", response_class=HTMLResponse)
async def registrar_visita(
    request: Request, usuario: dict = Depends(con_permiso(seg.REGISTRAR_VISITAS))
):
    valores = await formulario(request)
    respuesta = await api(request, "POST", URL_MEDICO, "/visitas", json=valores)

    if respuesta.status_code == 201:
        visita = respuesta.json()["visita"]
        return redirigir(f"/visitas/{visita['id']}", "Visita médica registrada.")

    mensaje, errores = _errores(respuesta)
    solicitud = await datos(request, URL_SOLICITUDES, f"/solicitudes/{valores.get('solicitud_id')}")
    return pagina(request, "visita_form.html", 422, solicitud=solicitud,
                  valores=valores, errores=errores, error=mensaje)


async def _detalle_visita(request, visita_id, codigo=200, error="", errores=None):
    visita = await datos(request, URL_MEDICO, f"/visitas/{visita_id}")
    paciente = await datos(request, URL_PACIENTES, f"/pacientes/{visita['paciente_id']}")
    tipos, medicamentos = [], []

    if tiene_permiso(request.state.usuario["rol"], seg.REGISTRAR_VISITAS):
        tipos = await datos(request, URL_MEDICO, "/tipos-examen")
        medicamentos = await datos(request, URL_MEDICO, "/medicamentos")

    return pagina(request, "visita_detalle.html", codigo, visita=visita, paciente=paciente,
                  tipos=tipos, medicamentos=medicamentos, error=error, errores=errores or {})


@app.get("/visitas/{visita_id}", response_class=HTMLResponse)
async def ver_visita(
    request: Request, visita_id: int,
    usuario: dict = Depends(con_permiso(seg.LEER_VISITAS))
):
    return await _detalle_visita(request, visita_id)


async def _agregar_a_visita(request, visita_id, ruta, mensaje_exito):
    valores = await formulario(request)
    respuesta = await api(request, "POST", URL_MEDICO, f"/visitas/{visita_id}{ruta}", json=valores)

    if respuesta.status_code == 201:
        return redirigir(f"/visitas/{visita_id}", mensaje_exito)

    mensaje, errores = _errores(respuesta)
    return await _detalle_visita(request, visita_id, 422, mensaje, errores)


@app.post("/visitas/{visita_id}/examenes", response_class=HTMLResponse)
async def solicitar_examen(
    request: Request, visita_id: int,
    usuario: dict = Depends(con_permiso(seg.REGISTRAR_VISITAS))
):
    return await _agregar_a_visita(request, visita_id, "/examenes",
                                   "Examen solicitado al laboratorio.")


@app.post("/visitas/{visita_id}/recetas", response_class=HTMLResponse)
async def indicar_medicamento(
    request: Request, visita_id: int,
    usuario: dict = Depends(con_permiso(seg.REGISTRAR_VISITAS))
):
    return await _agregar_a_visita(request, visita_id, "/recetas",
                                   "Medicamento indicado; puede recogerse en farmacia.")


# ==================================================
# LABORATORIO
# ==================================================

async def _pagina_laboratorio(request, estado, paciente_id, codigo=200, error=""):
    examenes = await datos(request, URL_MEDICO, "/examenes",
                           estado=estado, paciente_id=paciente_id)
    return pagina(request, "laboratorio.html", codigo, examenes=examenes, estado=estado,
                  paciente_id=paciente_id, pacientes=await _pacientes(request),
                  nombres=await _nombres_pacientes(request), error=error)


@app.get("/laboratorio", response_class=HTMLResponse)
async def laboratorio(
    request: Request, estado: str = "Solicitado", paciente_id: str = "",
    usuario: dict = Depends(con_permiso(seg.LEER_LABORATORIO))
):
    estado = estado if estado in ("Solicitado", "Completado") else ""
    return await _pagina_laboratorio(request, estado, paciente_id)


@app.post("/laboratorio/{examen_id}/resultado", response_class=HTMLResponse)
async def registrar_resultado(
    request: Request, examen_id: int,
    usuario: dict = Depends(con_permiso(seg.REGISTRAR_RESULTADOS))
):
    valores = await formulario(request)
    respuesta = await api(request, "PUT", URL_MEDICO, f"/examenes/{examen_id}/resultado",
                          json=valores)

    if respuesta.status_code == 200:
        return redirigir("/laboratorio", "Resultado registrado; el médico ya puede consultarlo.")

    return await _pagina_laboratorio(request, "Solicitado", "", 422, _errores(respuesta)[0])


# ==================================================
# FARMACIA
# ==================================================

async def _pagina_farmacia(request, estado, codigo=200, error=""):
    recetas = await datos(request, URL_MEDICO, "/recetas", estado=estado)
    return pagina(request, "farmacia.html", codigo, recetas=recetas, estado=estado,
                  medicamentos=await datos(request, URL_MEDICO, "/medicamentos"),
                  nombres=await _nombres_pacientes(request), error=error)


@app.get("/farmacia", response_class=HTMLResponse)
async def farmacia(
    request: Request, estado: str = "Pendiente de entrega",
    usuario: dict = Depends(con_permiso(seg.LEER_FARMACIA))
):
    estado = estado if estado in ("Pendiente de entrega", "Entregado") else ""
    return await _pagina_farmacia(request, estado)


@app.post("/farmacia/{receta_id}/entregar", response_class=HTMLResponse)
async def entregar_medicamento(
    request: Request, receta_id: int,
    usuario: dict = Depends(con_permiso(seg.ENTREGAR_MEDICAMENTOS))
):
    respuesta = await api(request, "PUT", URL_MEDICO, f"/recetas/{receta_id}/entrega")

    if respuesta.status_code == 200:
        return redirigir("/farmacia", "Entrega registrada y costo cargado a la visita.")

    return await _pagina_farmacia(request, "Pendiente de entrega", 409, _errores(respuesta)[0])


# ==================================================
# MÉDICOS Y CATÁLOGOS
# Todos los catálogos usan las mismas pantallas; aquí se
# definen sus campos.
# ==================================================

CATALOGOS = {
    "especialidades": {
        "titulo": "Especialidades", "editar": seg.EDITAR_CATALOGOS,
        "campos": [
            {"nombre": "nombre", "etiqueta": "Nombre", "requerido": True},
            {"nombre": "precio_consulta", "etiqueta": "Precio de consulta (Q)",
             "tipo": "number", "requerido": True, "moneda": True},
        ]
    },
    "medicos": {
        "titulo": "Médicos", "editar": seg.EDITAR_CATALOGOS,
        "campos": [
            {"nombre": "nombre", "etiqueta": "Nombre", "requerido": True},
            {"nombre": "especialidad_id", "etiqueta": "Especialidad", "tipo": "select",
             "requerido": True, "catalogo": "especialidades", "mostrar": "especialidad"},
            {"nombre": "colegiado", "etiqueta": "No. de colegiado", "requerido": True},
            {"nombre": "telefono", "etiqueta": "Teléfono"},
        ]
    },
    "enfermeros": {
        "titulo": "Enfermeros(as)", "editar": seg.EDITAR_ENFERMEROS,
        "campos": [
            {"nombre": "nombre", "etiqueta": "Nombre", "requerido": True},
            {"nombre": "turno", "etiqueta": "Turno", "tipo": "select", "requerido": True,
             "opciones": [("Mañana", "Mañana"), ("Tarde", "Tarde"), ("Noche", "Noche")]},
            {"nombre": "telefono", "etiqueta": "Teléfono"},
        ]
    },
    "tipos-examen": {
        "titulo": "Exámenes de laboratorio", "editar": seg.EDITAR_CATALOGOS,
        "campos": [
            {"nombre": "nombre", "etiqueta": "Examen", "requerido": True},
            {"nombre": "precio", "etiqueta": "Precio (Q)", "tipo": "number",
             "requerido": True, "moneda": True},
        ]
    },
    "medicamentos": {
        "titulo": "Medicamentos", "editar": seg.EDITAR_CATALOGOS,
        "campos": [
            {"nombre": "nombre", "etiqueta": "Medicamento", "requerido": True},
            {"nombre": "presentacion", "etiqueta": "Presentación", "requerido": True},
            {"nombre": "precio_unitario", "etiqueta": "Precio unitario (Q)", "tipo": "number",
             "requerido": True, "moneda": True},
            {"nombre": "existencia", "etiqueta": "Existencia", "tipo": "number",
             "paso": "1", "requerido": True},
        ]
    },
}


def _catalogo(tipo):
    if tipo not in CATALOGOS:
        raise ErrorPagina("No encontrado", "El catálogo solicitado no existe.", 404)
    return CATALOGOS[tipo]


async def _opciones_catalogo(request, catalogo):
    """Agrega a los campos de selección las opciones de otro catálogo."""

    campos = []
    for campo in catalogo["campos"]:
        campo = dict(campo)
        if "catalogo" in campo:
            registros = await datos(request, URL_MEDICO, f"/{campo['catalogo']}")
            campo["opciones"] = [(r["id"], r["nombre"]) for r in registros]
        campos.append(campo)
    return campos


@app.get("/catalogos", response_class=HTMLResponse)
async def catalogos(
    request: Request, usuario: dict = Depends(con_permiso(seg.LEER_CATALOGOS))
):
    configuracion = await datos(request, URL_MEDICO, "/configuracion")
    resumen = {tipo: len(await datos(request, URL_MEDICO, f"/{tipo}")) for tipo in CATALOGOS}
    return pagina(request, "catalogos.html", catalogos=CATALOGOS, resumen=resumen,
                  configuracion=configuracion, errores={})


@app.post("/catalogos/configuracion", response_class=HTMLResponse)
async def guardar_configuracion(
    request: Request, usuario: dict = Depends(con_permiso(seg.EDITAR_CATALOGOS))
):
    valores = await formulario(request)
    respuesta = await api(request, "PUT", URL_MEDICO, "/configuracion", json=valores)

    if respuesta.status_code == 200:
        return redirigir("/catalogos", "Descuento de la fundación actualizado.")

    mensaje, errores = _errores(respuesta)
    resumen = {tipo: len(await datos(request, URL_MEDICO, f"/{tipo}")) for tipo in CATALOGOS}
    return pagina(request, "catalogos.html", 422, catalogos=CATALOGOS, resumen=resumen,
                  configuracion=valores, errores=errores, error=mensaje)


async def _pagina_catalogo(request, tipo, codigo=200, valores=None, errores=None, error=""):
    catalogo = _catalogo(tipo)
    return pagina(
        request, "catalogo.html", codigo,
        tipo=tipo, catalogo=catalogo, campos=await _opciones_catalogo(request, catalogo),
        registros=await datos(request, URL_MEDICO, f"/{tipo}"),
        valores=valores or {}, errores=errores or {}, error=error
    )


@app.get("/catalogos/{tipo}", response_class=HTMLResponse)
async def ver_catalogo(
    request: Request, tipo: str, usuario: dict = Depends(con_permiso(seg.LEER_CATALOGOS))
):
    return await _pagina_catalogo(request, tipo)


@app.post("/catalogos/{tipo}", response_class=HTMLResponse)
async def agregar_a_catalogo(
    request: Request, tipo: str, usuario: dict = Depends(sesion)
):
    if not tiene_permiso(usuario["rol"], _catalogo(tipo)["editar"]):
        raise sin_permiso()

    valores = await formulario(request)
    respuesta = await api(request, "POST", URL_MEDICO, f"/{tipo}", json=valores)

    if respuesta.status_code == 201:
        return redirigir(f"/catalogos/{tipo}", "Registro agregado correctamente.")

    mensaje, errores = _errores(respuesta)
    return await _pagina_catalogo(request, tipo, 422, valores, errores, mensaje)


async def _editor_catalogo(request, tipo, registro, codigo=200, errores=None, error=""):
    catalogo = _catalogo(tipo)
    return pagina(request, "catalogo_editar.html", codigo, tipo=tipo, catalogo=catalogo,
                  campos=await _opciones_catalogo(request, catalogo), registro=registro,
                  errores=errores or {}, error=error)


@app.get("/catalogos/{tipo}/{registro_id}", response_class=HTMLResponse)
async def editar_catalogo(
    request: Request, tipo: str, registro_id: int, usuario: dict = Depends(sesion)
):
    if not tiene_permiso(usuario["rol"], _catalogo(tipo)["editar"]):
        raise sin_permiso()

    registro = await datos(request, URL_MEDICO, f"/{tipo}/{registro_id}")
    return await _editor_catalogo(request, tipo, registro)


@app.post("/catalogos/{tipo}/{registro_id}", response_class=HTMLResponse)
async def guardar_catalogo(
    request: Request, tipo: str, registro_id: int, usuario: dict = Depends(sesion)
):
    catalogo = _catalogo(tipo)

    if not tiene_permiso(usuario["rol"], catalogo["editar"]):
        raise sin_permiso()

    opcionales = [c["nombre"] for c in catalogo["campos"] if not c.get("requerido")]
    valores = await formulario(request, *opcionales)

    for campo in catalogo["campos"]:
        if campo.get("requerido"):
            valores.setdefault(campo["nombre"], "")

    respuesta = await api(request, "PUT", URL_MEDICO, f"/{tipo}/{registro_id}", json=valores)

    if respuesta.status_code == 200:
        return redirigir(f"/catalogos/{tipo}", "Registro actualizado correctamente.")

    mensaje, errores = _errores(respuesta)
    return await _editor_catalogo(request, tipo, {**valores, "id": registro_id}, 422,
                                  errores, mensaje)


# ==================================================
# FINANZAS
# ==================================================

MOVIMIENTOS = {
    "donaciones": {
        "titulo": "Donaciones", "tipo": "Entrada",
        "campos": [
            {"nombre": "fecha", "etiqueta": "Fecha", "tipo": "date"},
            {"nombre": "tipo_donante", "etiqueta": "Tipo de donante", "tipo": "select",
             "requerido": True, "opciones": [(t, t) for t in (
                 "Empresa internacional", "Empresa nacional", "Gobierno", "Persona particular")]},
            {"nombre": "donante", "etiqueta": "Donante", "requerido": True},
            {"nombre": "monto", "etiqueta": "Monto (Q)", "tipo": "number",
             "requerido": True, "moneda": True},
            {"nombre": "descripcion", "etiqueta": "Descripción"},
        ]
    },
    "cuotas": {
        "titulo": "Cuotas mensuales de familiares", "tipo": "Entrada",
        "campos": [
            {"nombre": "fecha", "etiqueta": "Fecha de pago", "tipo": "date"},
            {"nombre": "paciente_id", "etiqueta": "Paciente", "tipo": "select",
             "requerido": True, "pacientes": True, "mostrar": "paciente"},
            {"nombre": "mes", "etiqueta": "Mes que paga", "tipo": "month", "requerido": True},
            {"nombre": "monto", "etiqueta": "Monto (Q)", "tipo": "number",
             "requerido": True, "moneda": True},
            {"nombre": "observaciones", "etiqueta": "Observaciones"},
        ]
    },
    "cobros": {
        "titulo": "Cobros de citas médicas", "tipo": "Entrada", "solo_lectura": True,
        "campos": [
            {"nombre": "fecha", "etiqueta": "Fecha", "tipo": "date"},
            {"nombre": "paciente", "etiqueta": "Paciente"},
            {"nombre": "visita_id", "etiqueta": "Visita"},
            {"nombre": "monto", "etiqueta": "Monto (Q)", "moneda": True},
            {"nombre": "observaciones", "etiqueta": "Observaciones"},
        ]
    },
    "gastos": {
        "titulo": "Gastos", "tipo": "Salida",
        "campos": [
            {"nombre": "fecha", "etiqueta": "Fecha", "tipo": "date"},
            {"nombre": "categoria", "etiqueta": "Categoría", "tipo": "select",
             "requerido": True, "opciones": [(c, c) for c in (
                 "Luz", "Agua", "Alimentación", "Mantenimiento", "Salarios",
                 "Medicamentos", "Limpieza", "Otros")]},
            {"nombre": "descripcion", "etiqueta": "Descripción", "requerido": True},
            {"nombre": "monto", "etiqueta": "Monto (Q)", "tipo": "number",
             "requerido": True, "moneda": True},
        ]
    },
    "pagos-fundacion": {
        "titulo": "Pagos a la fundación", "tipo": "Salida",
        "campos": [
            {"nombre": "fecha", "etiqueta": "Fecha", "tipo": "date"},
            {"nombre": "monto", "etiqueta": "Monto (Q)", "tipo": "number",
             "requerido": True, "moneda": True},
            {"nombre": "referencia", "etiqueta": "Referencia (cheque, transferencia...)"},
        ]
    },
}


@app.get("/finanzas", response_class=HTMLResponse)
async def finanzas(request: Request, usuario: dict = Depends(con_permiso(seg.FINANZAS))):
    fechas = _parametros_fecha(request)
    resumen = await datos(request, URL_FINANZAS, "/resumen", **fechas)
    return pagina(request, "finanzas.html", resumen=resumen, movimientos=MOVIMIENTOS, **fechas)


async def _pagina_movimientos(request, tipo, codigo=200, valores=None, errores=None, error=""):
    if tipo not in MOVIMIENTOS:
        raise ErrorPagina("No encontrado", "La sección solicitada no existe.", 404)

    movimiento = MOVIMIENTOS[tipo]
    fechas = _parametros_fecha(request)
    campos = [dict(c) for c in movimiento["campos"]]

    for campo in campos:
        if campo.get("pacientes"):
            campo["opciones"] = [(p["id"], p["nombre"]) for p in await _pacientes(request)]

    registros = await datos(request, URL_FINANZAS, f"/{tipo}", **fechas)
    extra = {}
    if tipo == "pagos-fundacion":
        extra["fundacion"] = await datos(request, URL_FINANZAS, "/fundacion")

    return pagina(
        request, "movimientos.html", codigo,
        tipo=tipo, movimiento=movimiento, campos=campos, registros=registros,
        total=round(sum(r["monto"] for r in registros), 2),
        valores=valores or {}, errores=errores or {}, error=error, **fechas, **extra
    )


@app.get("/finanzas/cuentas", response_class=HTMLResponse)
async def cuentas(request: Request, usuario: dict = Depends(con_permiso(seg.FINANZAS))):
    return pagina(request, "cuentas.html",
                  cuentas=await datos(request, URL_FINANZAS, "/cuentas"))


async def _pagina_cuenta(request, paciente_id, codigo=200, errores=None, error="", valores=None):
    cuenta = await datos(request, URL_FINANZAS, f"/cuentas/{paciente_id}")
    return pagina(request, "cuenta_paciente.html", codigo, cuenta=cuenta,
                  errores=errores or {}, error=error, valores=valores or {})


@app.get("/finanzas/cuentas/{paciente_id}", response_class=HTMLResponse)
async def cuenta_paciente(
    request: Request, paciente_id: int, usuario: dict = Depends(con_permiso(seg.FINANZAS))
):
    return await _pagina_cuenta(request, paciente_id)


@app.post("/finanzas/cuentas/{paciente_id}/cobro", response_class=HTMLResponse)
async def registrar_cobro(
    request: Request, paciente_id: int, usuario: dict = Depends(con_permiso(seg.FINANZAS))
):
    valores = await formulario(request)
    valores["paciente_id"] = paciente_id
    respuesta = await api(request, "POST", URL_FINANZAS, "/cobros", json=valores)

    if respuesta.status_code == 201:
        return redirigir(f"/finanzas/cuentas/{paciente_id}", "Cobro registrado correctamente.")

    mensaje, errores = _errores(respuesta)
    return await _pagina_cuenta(request, paciente_id, 422, errores, mensaje, valores)


@app.get("/finanzas/{tipo}", response_class=HTMLResponse)
async def movimientos(
    request: Request, tipo: str, usuario: dict = Depends(con_permiso(seg.FINANZAS))
):
    return await _pagina_movimientos(request, tipo)


@app.post("/finanzas/{tipo}", response_class=HTMLResponse)
async def registrar_movimiento(
    request: Request, tipo: str, usuario: dict = Depends(con_permiso(seg.FINANZAS))
):
    if tipo not in MOVIMIENTOS or MOVIMIENTOS[tipo].get("solo_lectura"):
        raise ErrorPagina("Operación no permitida", "Esta sección no admite registros.", 405)

    valores = await formulario(request)
    respuesta = await api(request, "POST", URL_FINANZAS, f"/{tipo}", json=valores)

    if respuesta.status_code == 201:
        return redirigir(f"/finanzas/{tipo}", "Registro guardado correctamente.")

    mensaje, errores = _errores(respuesta)
    return await _pagina_movimientos(request, tipo, 422, valores, errores, mensaje)


# ==================================================
# REPORTES
# Cada reporte devuelve secciones con columnas y filas
# que la misma plantilla muestra como tablas.
# ==================================================

def _seccion(titulo, columnas, filas, total=None):
    return {"titulo": titulo, "columnas": columnas, "filas": filas, "total": total}


def _fecha_en_rango(fecha, desde, hasta):
    dia = (fecha or "")[:10]
    return bool(dia) and (not desde or dia >= desde) and (not hasta or dia <= hasta)


async def _reporte_costos_por_cita(request, paciente_id, desde, hasta):
    secciones = []
    pacientes = await _pacientes(request)

    for paciente in pacientes:
        if paciente_id and str(paciente["id"]) != paciente_id:
            continue

        cuenta = await datos(request, URL_FINANZAS, f"/cuentas/{paciente['id']}")
        for visita in cuenta["visitas"]:
            if not _fecha_en_rango(visita["fecha"], desde, hasta):
                continue
            filas = [[c["tipo"], c["descripcion"], _formato_fecha(c["fecha"]),
                      _formato_moneda(c["precio_regular"]), f"{c['descuento_pct']:g} %",
                      _formato_moneda(c["monto"])] for c in visita["cargos"]]
            secciones.append(_seccion(
                f"{paciente['nombre']} — visita #{visita['visita_id']} "
                f"({_formato_fecha(visita['fecha'])}) — {visita['estado']}",
                ["Tipo", "Detalle", "Fecha", "Precio regular", "Descuento", "Costo"],
                filas, _formato_moneda(visita["total"])
            ))

    return secciones


async def _reporte_analisis_medico(request, paciente_id, desde, hasta):
    if not paciente_id:
        return []

    ficha = await datos(request, URL_MEDICO, f"/fichas/{paciente_id}")
    paciente, antecedentes = ficha["paciente"], ficha["ficha"]

    secciones = [_seccion("Datos del paciente y ficha médica", ["Dato", "Valor"], [
        ["Paciente", paciente["nombre"]],
        ["Edad", paciente["edad"]],
        ["Fecha de ingreso", _formato_fecha(paciente.get("fecha_ingreso"))],
        ["Motivo de ingreso al asilo", paciente.get("motivo_ingreso") or "—"],
        ["Tipo de sangre", antecedentes["tipo_sangre"] or "—"],
        ["Alergias", antecedentes["alergias"] or "—"],
        ["Psicopatología", antecedentes["psicopatologia"] or "—"],
        ["Enfermedades crónicas", antecedentes["enfermedades_cronicas"] or "—"],
        ["Medicamentos de base", antecedentes["medicamentos_base"] or "—"],
    ])]

    visitas = [v for v in ficha["historial"] if _fecha_en_rango(v["fecha"], desde, hasta)]
    secciones.append(_seccion("Visitas médicas", [
        "Fecha", "Médico", "Especialidad", "Motivo", "Diagnóstico", "Observaciones"
    ], [[_formato_fecha(v["fecha"]), v["medico"], v["especialidad"], v["motivo"],
         v["diagnostico"], v["observaciones"] or "—"] for v in visitas]))

    secciones.append(_seccion("Medicamentos indicados", [
        "Fecha", "Medicamento", "Cantidad", "Cómo tomarlo", "Duración", "Estado"
    ], [[_formato_fecha(r["fecha_indicacion"]), r["medicamento"], r["cantidad"],
         r["indicaciones"], r["duracion"], r["estado"]]
        for v in visitas for r in v["recetas"]]))

    return secciones


async def _reporte_cobros(request, paciente_id, desde, hasta):
    cobros = await datos(request, URL_FINANZAS, "/cobros",
                         paciente_id=paciente_id, desde=desde, hasta=hasta)
    secciones = [_seccion("Cobros", ["Fecha", "Paciente", "Visita", "Monto", "Observaciones"], [
        [_formato_fecha(c["fecha"]), c["paciente"], f"#{c['visita_id']}",
         _formato_moneda(c["monto"]), c["observaciones"] or "—"] for c in cobros
    ], _formato_moneda(sum(c["monto"] for c in cobros)))]

    # Detalle de los gastos médicos de las visitas cobradas.
    for visita_id in sorted({c["visita_id"] for c in cobros}):
        paciente = next(c["paciente_id"] for c in cobros if c["visita_id"] == visita_id)
        cuenta = await datos(request, URL_FINANZAS, f"/cuentas/{paciente}")
        for visita in cuenta["visitas"]:
            if visita["visita_id"] == visita_id:
                secciones.append(_seccion(
                    f"Detalle de gastos médicos — visita #{visita_id} ({cuenta['paciente']['nombre']})",
                    ["Tipo", "Detalle", "Costo"],
                    [[c["tipo"], c["descripcion"], _formato_moneda(c["monto"])] for c in visita["cargos"]],
                    f"{_formato_moneda(visita['total'])} — pagado {_formato_moneda(visita['pagado'])}"
                ))

    return secciones


async def _reporte_pagos_fundacion(request, paciente_id, desde, hasta):
    pagos = await datos(request, URL_FINANZAS, "/pagos-fundacion", desde=desde, hasta=hasta)
    estado = await datos(request, URL_FINANZAS, "/fundacion")
    return [
        _seccion("Pagos realizados", ["Fecha", "Referencia", "Monto", "Registrado por"], [
            [_formato_fecha(p["fecha"]), p["referencia"] or "—", _formato_moneda(p["monto"]),
             p["registrado_por"]] for p in pagos
        ], _formato_moneda(sum(p["monto"] for p in pagos))),
        _seccion("Estado de cuenta con la fundación", ["Concepto", "Monto"], [
            ["Total de servicios recibidos (con descuento)", _formato_moneda(estado["total_cargos"])],
            ["Total pagado", _formato_moneda(estado["pagado"])],
            ["Saldo pendiente", _formato_moneda(estado["saldo"])],
        ])
    ]


async def _reporte_entradas(request, paciente_id, desde, hasta):
    donaciones = await datos(request, URL_FINANZAS, "/donaciones", desde=desde, hasta=hasta)
    cuotas = await datos(request, URL_FINANZAS, "/cuotas", desde=desde, hasta=hasta)
    cobros = await datos(request, URL_FINANZAS, "/cobros", desde=desde, hasta=hasta)

    return [
        _seccion("Donaciones", ["Fecha", "Tipo de donante", "Donante", "Monto"], [
            [_formato_fecha(d["fecha"]), d["tipo_donante"], d["donante"], _formato_moneda(d["monto"])]
            for d in donaciones
        ], _formato_moneda(sum(d["monto"] for d in donaciones))),
        _seccion("Cuotas familiares", ["Fecha", "Paciente", "Mes", "Monto"], [
            [_formato_fecha(c["fecha"]), c["paciente"], c["mes"], _formato_moneda(c["monto"])]
            for c in cuotas
        ], _formato_moneda(sum(c["monto"] for c in cuotas))),
        _seccion("Cobros de citas", ["Fecha", "Paciente", "Visita", "Monto"], [
            [_formato_fecha(c["fecha"]), c["paciente"], f"#{c['visita_id']}", _formato_moneda(c["monto"])]
            for c in cobros
        ], _formato_moneda(sum(c["monto"] for c in cobros))),
        _seccion("Total de entradas", ["Concepto", "Monto"], [], _formato_moneda(
            sum(r["monto"] for r in (*donaciones, *cuotas, *cobros))
        )),
    ]


async def _reporte_examenes(request, paciente_id, desde, hasta):
    examenes = await datos(request, URL_MEDICO, "/examenes", paciente_id=paciente_id)
    nombres = await _nombres_pacientes(request)
    examenes = [e for e in examenes if _fecha_en_rango(e["fecha_solicitud"], desde, hasta)]

    return [_seccion("Exámenes de laboratorio", [
        "Paciente", "Examen", "Solicitado", "Estado", "Resultado", "Fecha de resultado"
    ], [[nombres.get(e["paciente_id"], e["paciente_id"]), e["examen"],
         _formato_fecha(e["fecha_solicitud"]), e["estado"], e["resultado"] or "—",
         _formato_fecha(e["fecha_resultado"])] for e in examenes])]


async def _reporte_medicamentos(request, paciente_id, desde, hasta):
    recetas = await datos(request, URL_MEDICO, "/recetas", paciente_id=paciente_id)
    nombres = await _nombres_pacientes(request)
    recetas = [r for r in recetas if _fecha_en_rango(r["fecha_indicacion"], desde, hasta)]

    return [_seccion("Medicamentos aplicados", [
        "Paciente", "Medicamento", "Cantidad", "Cómo tomarlo", "Duración", "Indicado", "Entregado"
    ], [[nombres.get(r["paciente_id"], r["paciente_id"]), r["medicamento"], r["cantidad"],
         r["indicaciones"], r["duracion"], _formato_fecha(r["fecha_indicacion"]),
         _formato_fecha(r["fecha_entrega"])] for r in recetas])]


REPORTES = {
    "costos-por-cita": {
        "titulo": "Costos de cada cita por paciente",
        "descripcion": "Consulta, exámenes de laboratorio y medicamentos de cada visita.",
        "roles": seg.FINANZAS, "generar": _reporte_costos_por_cita},
    "analisis-medico": {
        "titulo": "Análisis médico por paciente",
        "descripcion": "Ficha médica, motivo de ingreso, visitas y medicamentos.",
        "roles": seg.MEDICOS, "generar": _reporte_analisis_medico, "requiere_paciente": True},
    "cobros": {
        "titulo": "Cobros por paciente y rango de fechas",
        "descripcion": "Pagos de los familiares con el detalle de los gastos médicos.",
        "roles": seg.FINANZAS, "generar": _reporte_cobros},
    "pagos-fundacion": {
        "titulo": "Pagos a la fundación",
        "descripcion": "Pagos realizados y saldo pendiente con la fundación.",
        "roles": seg.FINANZAS, "generar": _reporte_pagos_fundacion, "sin_paciente": True},
    "entradas": {
        "titulo": "Entradas: donaciones y cobros",
        "descripcion": "Donaciones, cuotas familiares y cobros del periodo.",
        "roles": seg.FINANZAS, "generar": _reporte_entradas, "sin_paciente": True},
    "examenes": {
        "titulo": "Exámenes médicos realizados por paciente",
        "descripcion": "Exámenes solicitados, su estado y resultado.",
        "roles": (*seg.MEDICOS, seg.LABORATORIO), "generar": _reporte_examenes},
    "medicamentos": {
        "titulo": "Medicamentos aplicados por paciente",
        "descripcion": "Medicamentos indicados, cómo tomarlos y su entrega.",
        "roles": (*seg.MEDICOS, seg.FARMACIA), "generar": _reporte_medicamentos},
}

ROLES_REPORTES = next(m["roles"] for m in MODULOS if m["ruta"] == "/reportes")


@app.get("/reportes", response_class=HTMLResponse)
def reportes(request: Request, usuario: dict = Depends(con_permiso(ROLES_REPORTES))):
    disponibles = {
        clave: r for clave, r in REPORTES.items() if tiene_permiso(usuario["rol"], r["roles"])
    }
    return pagina(request, "reportes.html", reportes=disponibles)


@app.get("/reportes/{clave}", response_class=HTMLResponse)
async def ver_reporte(
    request: Request, clave: str, paciente_id: str = "", desde: str = "", hasta: str = "",
    usuario: dict = Depends(sesion)
):
    if clave not in REPORTES:
        raise ErrorPagina("No encontrado", "El reporte solicitado no existe.", 404)

    reporte = REPORTES[clave]

    if not tiene_permiso(usuario["rol"], reporte["roles"]):
        raise sin_permiso("Su rol no tiene permiso para ver este reporte.")

    for nombre, valor in (("desde", desde), ("hasta", hasta)):
        try:
            if valor:
                date.fromisoformat(valor)
        except ValueError:
            raise ErrorPagina("Fecha inválida", f"La fecha «{nombre}» debe tener el formato AAAA-MM-DD.")

    if desde and hasta and desde > hasta:
        raise ErrorPagina("Rango inválido", "La fecha inicial no puede ser posterior a la final.")

    pacientes = [] if reporte.get("sin_paciente") else await _pacientes(request)
    secciones = await reporte["generar"](request, paciente_id, desde, hasta)

    return pagina(
        request, "reporte.html", clave=clave, reporte=reporte, secciones=secciones,
        pacientes=pacientes, paciente_id=paciente_id, desde=desde, hasta=hasta,
        generado=datetime.now()
    )


# ==================================================
# CORREOS A FAMILIARES
# ==================================================

@app.get("/notificaciones", response_class=HTMLResponse)
async def notificaciones(
    request: Request, usuario: dict = Depends(con_permiso(seg.VER_NOTIFICACIONES))
):
    return pagina(request, "notificaciones.html",
                  correos=await datos(request, URL_SOLICITUDES, "/notificaciones"))


# ==================================================
# USUARIOS Y ROLES (administrador)
# ==================================================

solo_admin = con_permiso((ADMINISTRADOR,))


def _validar_usuario(valores, nuevo, usuario_id=None):
    errores = {}

    if nuevo:
        nombre_usuario = normalizar(valores.get("usuario", ""))
        if not nombre_usuario or " " in nombre_usuario:
            errores["usuario"] = "Escriba un nombre de usuario sin espacios."
        elif usuarios.listar(lambda u: u["usuario"] == nombre_usuario):
            errores["usuario"] = "Ese nombre de usuario ya existe."
        valores["usuario"] = nombre_usuario

    if not valores.get("nombre", "").strip():
        errores["nombre"] = "Este campo es obligatorio."

    if valores.get("rol") not in seg.ROLES:
        errores["rol"] = "Seleccione un rol válido."

    contrasena = valores.get("contrasena", "")
    if (nuevo or contrasena) and len(contrasena) < LONGITUD_MINIMA_CONTRASENA:
        errores["contrasena"] = f"La contraseña debe tener al menos {LONGITUD_MINIMA_CONTRASENA} caracteres."

    return errores


def _sin_contrasena(usuario):
    return {k: v for k, v in usuario.items() if k != "contrasena"}


@app.get("/usuarios", response_class=HTMLResponse)
def lista_usuarios(request: Request, usuario: dict = Depends(solo_admin)):
    lista = sorted((_sin_contrasena(u) for u in usuarios.listar()), key=lambda u: u["usuario"])
    return pagina(request, "usuarios.html", usuarios=lista, roles=seg.ROLES)


@app.get("/usuarios/nuevo", response_class=HTMLResponse)
def nuevo_usuario(request: Request, usuario: dict = Depends(solo_admin)):
    return pagina(request, "usuario_form.html", registro={"activo": True},
                  roles=seg.ROLES, errores={})


@app.post("/usuarios/nuevo", response_class=HTMLResponse)
async def crear_usuario(request: Request, usuario: dict = Depends(solo_admin)):
    valores = dict(await request.form())
    errores = _validar_usuario(valores, nuevo=True)

    if errores:
        valores.pop("contrasena", None)
        return pagina(request, "usuario_form.html", 422, registro=valores, roles=seg.ROLES,
                      errores=errores, error="Revise los campos marcados en rojo.")

    usuarios.agregar({
        "usuario": valores["usuario"],
        "nombre": valores["nombre"].strip(),
        "rol": valores["rol"],
        "activo": True,
        "contrasena": cifrar_contrasena(valores["contrasena"])
    })
    return redirigir("/usuarios", f"Usuario {valores['usuario']} creado correctamente.")


@app.get("/usuarios/{usuario_id}", response_class=HTMLResponse)
def editar_usuario(request: Request, usuario_id: int, usuario: dict = Depends(solo_admin)):
    registro = usuarios.obtener(usuario_id)

    if registro is None:
        raise ErrorPagina("No encontrado", "Usuario no encontrado.", 404)

    return pagina(request, "usuario_form.html", registro=_sin_contrasena(registro),
                  roles=seg.ROLES, errores={})


@app.post("/usuarios/{usuario_id}", response_class=HTMLResponse)
async def guardar_usuario(request: Request, usuario_id: int, usuario: dict = Depends(solo_admin)):
    registro = usuarios.obtener(usuario_id)

    if registro is None:
        raise ErrorPagina("No encontrado", "Usuario no encontrado.", 404)

    valores = dict(await request.form())
    errores = _validar_usuario(valores, nuevo=False)
    activo = valores.get("activo") == "si"

    if registro["usuario"] == usuario["usuario"] and (not activo or valores.get("rol") != ADMINISTRADOR):
        errores["rol"] = "No puede quitarse a sí mismo el rol de administrador ni desactivarse."

    if errores:
        return pagina(request, "usuario_form.html", 422,
                      registro={**_sin_contrasena(registro), **valores, "activo": activo},
                      roles=seg.ROLES, errores=errores, error="Revise los campos marcados en rojo.")

    cambios = {"nombre": valores["nombre"].strip(), "rol": valores["rol"], "activo": activo}
    if valores.get("contrasena"):
        cambios["contrasena"] = cifrar_contrasena(valores["contrasena"])

    usuarios.actualizar(usuario_id, cambios)
    return redirigir("/usuarios", f"Usuario {registro['usuario']} actualizado.")
