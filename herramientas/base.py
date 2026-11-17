"""Interfaz común de las herramientas que Aline puede usar.

Una herramienta es una acción concreta (buscar, leer, crear...). El modelo
solo ve su nombre, descripción y parámetros; quien la ejecuta es el código,
así que aquí se decide qué se permite y qué no.
"""
from abc import ABC, abstractmethod


class ErrorHerramienta(Exception):
    """Error esperado (archivo inexistente, ruta prohibida...). Su mensaje
    se le devuelve al modelo para que corrija o le explique al usuario."""


class Herramienta(ABC):
    nombre: str = ""
    descripcion: str = ""
    parametros: dict = {"type": "object", "properties": {}, "required": []}
    requiere_confirmacion: bool = False

    # Frases habladas. Pueden usar {campo} con los argumentos de la llamada.
    aviso: dict[str, str] = {}          # lo que Aline dice al empezar
    confirmacion: dict[str, str] = {}   # la pregunta antes de ejecutar

    def esquema(self) -> dict:
        return {"nombre": self.nombre, "descripcion": self.descripcion, "parametros": self.parametros}

    def _formatear(self, plantillas: dict[str, str], args: dict, idioma: str) -> str | None:
        plantilla = plantillas.get(idioma) or plantillas.get("es")
        if not plantilla:
            return None
        recortados = {k: self._recortar(v) for k, v in args.items()}
        try:
            return plantilla.format(**recortados)
        except KeyError:
            return plantilla.split("{")[0].strip() or None

    @staticmethod
    def _recortar(valor, limite: int = 60) -> str:
        texto = str(valor).replace("\n", " ").strip()
        return texto if len(texto) <= limite else texto[: limite - 1] + "…"

    def texto_aviso(self, args: dict, idioma: str) -> str | None:
        return self._formatear(self.aviso, args, idioma)

    def texto_confirmacion(self, args: dict, idioma: str) -> str | None:
        return self._formatear(self.confirmacion, args, idioma)

    def filtrar_argumentos(self, args: dict) -> dict:
        """Descarta parámetros inventados por el modelo y verifica los obligatorios."""
        validos = self.parametros.get("properties", {})
        limpios = {k: v for k, v in args.items() if k in validos and v is not None}
        faltan = [r for r in self.parametros.get("required", []) if r not in limpios]
        if faltan:
            raise ErrorHerramienta(f"Faltan parámetros obligatorios: {', '.join(faltan)}")
        return limpios

    @abstractmethod
    def ejecutar(self, **args) -> str:
        """Hace la acción y devuelve un texto para el modelo."""
