"""Tipos comunes del "cerebro" de Aline.

El historial se guarda en un formato neutro, independiente del proveedor.
Cada adaptador (Ollama, Claude...) lo traduce al formato de su API.

Mensajes del historial:
    {"role": "user", "content": str}
    {"role": "assistant", "content": str, "llamadas": [LlamadaHerramienta, ...]}
    {"role": "herramienta", "id": str, "nombre": str, "content": str}
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LlamadaHerramienta:
    id: str
    nombre: str
    argumentos: dict


@dataclass
class RespuestaLLM:
    texto: str
    llamadas: list[LlamadaHerramienta] = field(default_factory=list)


class LLM(ABC):
    """Interfaz común. Cualquier proveedor nuevo solo debe implementar responder()."""

    @abstractmethod
    def responder(
        self,
        sistema: str,
        mensajes: list[dict],
        herramientas: list[dict] | None = None,
    ) -> RespuestaLLM:
        """sistema: prompt de personalidad e instrucciones.
        mensajes: historial en formato neutro (ver arriba).
        herramientas: esquemas {"nombre", "descripcion", "parametros"} o None."""
