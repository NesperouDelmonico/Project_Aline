from abc import ABC, abstractmethod


class TTS(ABC):
    """Interfaz común para cualquier motor de voz."""

    @abstractmethod
    def hablar(self, texto: str) -> None:
        """Convierte el texto en voz y lo reproduce (bloquea hasta terminar)."""
