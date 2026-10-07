"""Voz online con Fish Audio usando un modelo de voz elegido en fish.audio."""
import subprocess
import tempfile

from fishaudio import FishAudio
from fishaudio.core import RequestOptions
from fishaudio.types import Prosody, TTSConfig

from .base import TTS


class FishTTS(TTS):
    def __init__(self, api_key: str | None, voz_id: str, velocidad: float, modelo: str | None):
        if not api_key:
            raise ValueError("Falta FISH_API_KEY en el archivo .env")
        if not voz_id:
            raise ValueError("Falta FISH_VOZ_ID en config.py")
        self.cliente = FishAudio(api_key=api_key)
        self.config = TTSConfig(
            reference_id=voz_id,
            format="wav",
            latency="balanced",
            prosody=Prosody(speed=velocidad),
        )
        # Si no se indica modelo, Fish Audio usa el predeterminado de su API
        self.opciones = (
            RequestOptions(additional_headers={"model": modelo}) if modelo else None
        )

    def hablar(self, texto: str) -> None:
        audio = self.cliente.tts.convert(
            text=texto, config=self.config, request_options=self.opciones
        )
        # Se reproduce con PipeWire; el archivo temporal se borra al salir
        with tempfile.NamedTemporaryFile(suffix=".wav") as f:
            f.write(audio)
            f.flush()
            subprocess.run(["pw-play", f.name], check=False)
