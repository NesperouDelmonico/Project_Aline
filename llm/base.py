from abc import ABC, abstractmethod


class LLM(ABC):
    """Interfaz común. Cualquier proveedor nuevo solo debe implementar responder()."""

    @abstractmethod
    def responder(self, sistema: str, historial: list[dict]) -> str:
        """sistema: prompt de personalidad. historial: [{"role": ..., "content": ...}]"""
