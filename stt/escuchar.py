"""Oído de Alina: captura con speech_recognition, transcribe con faster-whisper."""
import numpy as np
import speech_recognition as sr
from faster_whisper import WhisperModel

import config
from utils.audio import silenciar_stderr


class Oido:
    def __init__(self):
        print(f"Cargando Whisper '{config.WHISPER_MODELO}' en {config.WHISPER_DEVICE}...")
        self.modelo = WhisperModel(
            config.WHISPER_MODELO,
            device=config.WHISPER_DEVICE,
            compute_type=config.WHISPER_COMPUTE,
        )
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = 0.8  # silencio que marca el fin de la frase
        self._calibrado = False
        self.ultimo_idioma: str | None = None  # código ISO detectado: "es", "en"...

    def _grabar(self) -> sr.AudioData | None:
        with silenciar_stderr():
            mic = sr.Microphone(device_index=config.MIC_DEVICE_INDEX)
            source = mic.__enter__()
        try:
            if not self._calibrado:
                print("Calibrando ruido ambiente...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                self._calibrado = True
            print("🎙️  Escuchando...")
            return self.recognizer.listen(
                source, timeout=config.ESPERA_MAX, phrase_time_limit=config.DURACION_MAX
            )
        except sr.WaitTimeoutError:
            return None
        finally:
            mic.__exit__(None, None, None)

    def escuchar(self) -> str | None:
        audio = self._grabar()
        if audio is None:
            return None

        # Whisper espera audio mono a 16 kHz en float32 entre -1 y 1
        crudo = audio.get_raw_data(convert_rate=16000, convert_width=2)
        muestras = np.frombuffer(crudo, dtype=np.int16).astype(np.float32) / 32768.0

        segmentos, info = self.modelo.transcribe(
            muestras, language=config.IDIOMA, beam_size=5, vad_filter=True
        )
        texto = " ".join(s.text.strip() for s in segmentos).strip()
        if texto:
            self.ultimo_idioma = info.language
            print(f"[{info.language}] Tú: {texto}")
        return texto or None
