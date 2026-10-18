from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from comun.repositorio import BaseDeDatosNoDisponible, RegistroRelacionado

# --------------------------------------------------
# TRADUCCIÓN DE LOS ERRORES DE VALIDACIÓN
# FastAPI devuelve los errores en inglés y con formato técnico;
# aquí se convierten en mensajes comprensibles en español.
# --------------------------------------------------


def _mensaje(error):
    tipo = error["type"]
    ctx = error.get("ctx", {})

    if tipo == "missing":
        return "Este campo es obligatorio."
    if tipo in ("int_parsing", "int_type", "int_from_float"):
        return "Debe ser un número entero."
    if tipo in ("float_parsing", "float_type", "decimal_parsing", "decimal_type"):
        return "Debe ser un número."
    if tipo == "string_type":
        return "Debe ser un texto."
    if tipo == "string_too_short":
        return "No puede quedar en blanco."
    if tipo == "string_too_long":
        return f"No puede tener más de {ctx.get('max_length')} caracteres."
    if tipo == "string_pattern_mismatch":
        return "El formato no es válido."
    if tipo == "greater_than":
        return f"Debe ser mayor que {ctx.get('gt')}."
    if tipo == "greater_than_equal":
        return f"Debe ser mayor o igual a {ctx.get('ge')}."
    if tipo == "less_than":
        return f"Debe ser menor que {ctx.get('lt')}."
    if tipo == "less_than_equal":
        return f"Debe ser menor o igual a {ctx.get('le')}."
    if tipo in ("literal_error", "enum"):
        return f"Valor no permitido. Opciones válidas: {ctx.get('expected')}."
    if tipo.startswith("date"):
        if "time" in tipo:
            return "Fecha y hora inválidas (formato AAAA-MM-DD HH:MM)."
        return "Fecha inválida (formato AAAA-MM-DD)."
    if tipo.startswith("datetime"):
        return "Fecha y hora inválidas (formato AAAA-MM-DD HH:MM)."
    if tipo == "bool_parsing":
        return "Debe ser verdadero o falso."
    if tipo == "json_invalid":
        return "La información enviada no tiene un formato JSON válido."
    if tipo in ("model_attributes_type", "dict_type"):
        return "Se esperaba un objeto con los datos del registro."
    if tipo == "extra_forbidden":
        return "Este campo no existe."
    if tipo == "value_error":
        return str(ctx.get("error", "Valor inválido."))

    return "Valor inválido."


def _campo(error):
    textos = [str(p) for p in error["loc"] if p not in ("body", "query", "path")]
    return ".".join(textos) or "datos"


def traducir_errores(errores):
    return [{"campo": _campo(e), "mensaje": _mensaje(e)} for e in errores]


def configurar_errores(app: FastAPI):

    @app.exception_handler(RequestValidationError)
    async def error_validacion(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "mensaje": "Los datos enviados no son válidos.",
                "errores": traducir_errores(exc.errors())
            }
        )

    @app.exception_handler(RegistroRelacionado)
    async def registro_relacionado(request: Request, exc: RegistroRelacionado):
        return JSONResponse(
            status_code=409,
            content={"mensaje": "No se puede eliminar: otros registros dependen de este."}
        )

    @app.exception_handler(BaseDeDatosNoDisponible)
    async def sin_base_de_datos(request: Request, exc: BaseDeDatosNoDisponible):
        return JSONResponse(
            status_code=503,
            content={"mensaje": "La base de datos no está disponible; intente más tarde."}
        )

    @app.exception_handler(StarletteHTTPException)
    async def error_http(request: Request, exc: StarletteHTTPException):
        mensaje = exc.detail
        if exc.status_code == 404 and mensaje == "Not Found":
            mensaje = "La dirección solicitada no existe."
        if exc.status_code == 405:
            mensaje = "Operación no permitida en esta dirección."

        contenido = {"mensaje": mensaje}
        if isinstance(exc, ErrorDeDatos):
            contenido["errores"] = [{"campo": exc.campo, "mensaje": mensaje}]

        return JSONResponse(
            status_code=exc.status_code,
            content=contenido,
            headers=getattr(exc, "headers", None)
        )


# --------------------------------------------------
# ERRORES DE NEGOCIO
# --------------------------------------------------

def no_encontrado(entidad):
    return HTTPException(status_code=404, detail=f"{entidad} no encontrado.")


class ErrorDeDatos(HTTPException):
    """Error 422 de una regla de negocio sobre un campo concreto."""

    def __init__(self, campo, mensaje):
        super().__init__(status_code=422, detail=mensaje)
        self.campo = campo


def datos_invalidos(campo, mensaje):
    return ErrorDeDatos(campo, mensaje)


def conflicto(mensaje):
    return HTTPException(status_code=409, detail=mensaje)
