"""Voz local y gratuita con pyttsx3 (espeak-ng). Sirve como respaldo sin internet."""
import pyttsx3

from utils.audio import silenciar_stderr

from .base import TTS


class EspeakTTS(TTS):
    def __init__(self, voz: str, velocidad: int):
        with silenciar_stderr():
            self.motor = pyttsx3.init()
        self.motor.setProperty("rate", velocidad)
        try:
            self.motor.setProperty("voice", voz)
        except Exception:
            print(f"No encontré la voz '{voz}', uso la predeterminada.")

    def hablar(self, texto: str) -> None:
        self.motor.say(texto)
        self.motor.runAndWait()
