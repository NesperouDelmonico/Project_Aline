import config

from .base import TTS


def crear_tts() -> TTS:
    """Devuelve el motor de voz elegido en config.py."""
    if config.TTS_PROVEEDOR == "espeak":
        from .espeak_tts import EspeakTTS
        return EspeakTTS(config.ESPEAK_VOZ, config.ESPEAK_VELOCIDAD)
    if config.TTS_PROVEEDOR == "fish":
        from .fish_tts import FishTTS
        return FishTTS(
            config.FISH_API_KEY, config.FISH_VOZ_ID, config.FISH_VELOCIDAD, config.FISH_MODELO
        )
    raise ValueError(f"Proveedor de voz desconocido: {config.TTS_PROVEEDOR}")
