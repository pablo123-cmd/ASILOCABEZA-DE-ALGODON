import httpx
from fastapi import HTTPException

from comun.config import NOMBRES_SERVICIOS
from comun.seguridad import token_servicio

# Las pruebas automáticas reemplazan la red por los servicios en
# memoria usando estos montajes (ver tests/conftest.py).
_montajes = {}


def configurar_montajes(montajes):
    _montajes.clear()
    _montajes.update(montajes)


class ServicioNoDisponible(Exception):

    def __init__(self, url_base):
        self.servicio = NOMBRES_SERVICIOS.get(url_base, url_base)
        super().__init__(f"El servicio de {self.servicio} no está disponible.")


async def pedir(metodo, url_base, ruta, token=None, **opciones):
    """
    Hace una petición a otro servicio. Si no se indica token se usa
    el token del servicio interno. Lanza ServicioNoDisponible cuando
    el servicio está apagado o no responde.
    """

    encabezados = {"Authorization": f"Bearer {token or token_servicio()}"}

    try:
        async with httpx.AsyncClient(
            base_url=url_base,
            headers=encabezados,
            timeout=5,
            mounts=dict(_montajes)
        ) as cliente:
            return await cliente.request(metodo, ruta, **opciones)

    except httpx.RequestError as error:
        raise ServicioNoDisponible(url_base) from error


async def obtener_o_none(url_base, ruta):
    """Consulta un registro de otro servicio; None si no existe."""

    try:
        respuesta = await pedir("GET", url_base, ruta)
    except ServicioNoDisponible as error:
        raise HTTPException(
            status_code=503,
            detail=f"{error} No se pudo validar la información; intente más tarde."
        )

    if respuesta.status_code == 404:
        return None

    respuesta.raise_for_status()
    return respuesta.json()
