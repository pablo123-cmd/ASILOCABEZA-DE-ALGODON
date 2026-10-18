import re
import unicodedata
from datetime import date
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

# --------------------------------------------------
# TIPOS DE DATO REUTILIZABLES
# Los textos se recortan antes de validar, así un campo formado
# solo por espacios se rechaza como vacío.
# --------------------------------------------------

Texto = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)
]

TextoLargo = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
]

TextoOpcional = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=2000)
]

Id = Annotated[int, Field(gt=0)]

Monto = Annotated[float, Field(gt=0, le=10_000_000)]

Porcentaje = Annotated[float, Field(ge=0, le=100)]

PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validar_correo(valor):
    if valor and not PATRON_CORREO.match(valor):
        raise ValueError("El correo electrónico no es válido.")
    return valor


CorreoOpcional = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=150),
    AfterValidator(_validar_correo)
]


def _validar_mes(valor):
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", valor):
        raise ValueError("El mes debe tener el formato AAAA-MM.")
    return valor


Mes = Annotated[
    str, StringConstraints(strip_whitespace=True), AfterValidator(_validar_mes)
]


class Modelo(BaseModel):
    """Modelo base: rechaza campos que no existen."""

    model_config = ConfigDict(extra="forbid")


def normalizar(texto):
    """Texto en minúsculas, sin acentos y con un solo espacio, para comparar nombres."""

    sin_acentos = "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )
    return " ".join(sin_acentos.casefold().split())


def en_rango(fecha_texto, desde: date | None, hasta: date | None):
    """Indica si una fecha ISO (AAAA-MM-DD...) está dentro del rango."""

    fecha = date.fromisoformat(fecha_texto[:10])
    return (desde is None or fecha >= desde) and (hasta is None or fecha <= hasta)
