import copy
import threading
from datetime import date, datetime
from decimal import Decimal

from comun import config


class RegistroRelacionado(Exception):
    """No se puede eliminar un registro que otros registros usan."""


class BaseDeDatosNoDisponible(Exception):
    """No hay conexión con MySQL."""


def crear_repositorio(tabla, iniciales=(), booleanos=()):
    """
    Repositorio de una entidad según la configuración (ASILO_BD).
    En MySQL los datos iniciales los carga el script docs/bd/asilo.sql.
    """

    if config.BASE_DE_DATOS == "memoria":
        return RepositorioMemoria(iniciales)

    return RepositorioMySQL(tabla, booleanos)


class RepositorioMemoria:
    """
    Guarda los registros de una entidad en memoria.

    Todos los servicios acceden a sus datos solo por medio de estos
    métodos (patrón Repository). Cuando se conecte la base de datos
    bastará con crear un repositorio con los mismos métodos que lea y
    escriba en ella; el resto del código no cambia.

    Los identificadores salen de un contador que nunca retrocede, por
    lo que un id no se repite aunque se eliminen registros.
    """

    def __init__(self, iniciales=()):
        self._datos = {}
        self._siguiente_id = 1
        self._candado = threading.Lock()

        for registro in iniciales:
            self.agregar(registro)

    def listar(self, filtro=None):
        with self._candado:
            registros = [copy.deepcopy(r) for r in self._datos.values()]

        if filtro:
            registros = [r for r in registros if filtro(r)]

        return registros

    def obtener(self, registro_id):
        with self._candado:
            registro = self._datos.get(registro_id)
            return copy.deepcopy(registro) if registro else None

    def agregar(self, datos):
        with self._candado:
            registro = copy.deepcopy(datos)
            registro["id"] = self._siguiente_id
            self._siguiente_id += 1
            self._datos[registro["id"]] = registro
            return copy.deepcopy(registro)

    def actualizar(self, registro_id, cambios):
        with self._candado:
            registro = self._datos.get(registro_id)

            if registro is None:
                return None

            registro.update(copy.deepcopy(cambios))
            registro["id"] = registro_id
            return copy.deepcopy(registro)

    def eliminar(self, registro_id):
        with self._candado:
            return self._datos.pop(registro_id, None) is not None


class RepositorioMySQL:
    """
    Guarda los registros de una entidad en una tabla de MySQL.

    Tiene los mismos métodos que RepositorioMemoria y devuelve los
    mismos tipos (fechas como texto ISO, montos como float), así que
    los servicios no notan la diferencia.
    """

    def __init__(self, tabla, booleanos=()):
        self._tabla = tabla
        self._booleanos = set(booleanos)

    def _conectar(self):
        import pymysql

        try:
            return pymysql.connect(
                host=config.MYSQL_HOST,
                port=config.MYSQL_PUERTO,
                user=config.MYSQL_USUARIO,
                password=config.MYSQL_CONTRASENA,
                database=config.MYSQL_BD,
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True,
                connect_timeout=5
            )
        except pymysql.err.OperationalError as error:
            raise BaseDeDatosNoDisponible(str(error)) from error

    def _ejecutar(self, sql, valores=()):
        import pymysql

        conexion = self._conectar()
        try:
            with conexion.cursor() as cursor:
                cursor.execute(sql, valores)
                return cursor.fetchall(), cursor.lastrowid, cursor.rowcount
        except pymysql.err.IntegrityError as error:
            if error.args[0] == 1451:
                raise RegistroRelacionado() from error
            raise
        except pymysql.err.OperationalError as error:
            raise BaseDeDatosNoDisponible(str(error)) from error
        finally:
            conexion.close()

    def _a_registro(self, fila):
        registro = {}

        for campo, valor in fila.items():
            if isinstance(valor, datetime):
                valor = valor.isoformat(timespec="minutes")
            elif isinstance(valor, date):
                valor = valor.isoformat()
            elif isinstance(valor, Decimal):
                valor = float(valor)
            elif campo in self._booleanos and valor is not None:
                valor = bool(valor)
            registro[campo] = valor

        return registro

    def listar(self, filtro=None):
        filas, _, _ = self._ejecutar(f"SELECT * FROM `{self._tabla}` ORDER BY id")
        registros = [self._a_registro(f) for f in filas]

        if filtro:
            registros = [r for r in registros if filtro(r)]

        return registros

    def obtener(self, registro_id):
        filas, _, _ = self._ejecutar(
            f"SELECT * FROM `{self._tabla}` WHERE id = %s", (registro_id,)
        )
        return self._a_registro(filas[0]) if filas else None

    def agregar(self, datos):
        campos = [c for c in datos if c != "id"]
        columnas = ", ".join(f"`{c}`" for c in campos)
        marcas = ", ".join(["%s"] * len(campos))

        _, nuevo_id, _ = self._ejecutar(
            f"INSERT INTO `{self._tabla}` ({columnas}) VALUES ({marcas})",
            [datos[c] for c in campos]
        )
        return self.obtener(nuevo_id)

    def actualizar(self, registro_id, cambios):
        campos = [c for c in cambios if c != "id"]

        if campos:
            asignaciones = ", ".join(f"`{c}` = %s" for c in campos)
            self._ejecutar(
                f"UPDATE `{self._tabla}` SET {asignaciones} WHERE id = %s",
                [cambios[c] for c in campos] + [registro_id]
            )

        return self.obtener(registro_id)

    def eliminar(self, registro_id):
        _, _, filas = self._ejecutar(
            f"DELETE FROM `{self._tabla}` WHERE id = %s", (registro_id,)
        )
        return filas > 0
