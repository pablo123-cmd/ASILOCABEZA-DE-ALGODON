import copy
import threading


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
