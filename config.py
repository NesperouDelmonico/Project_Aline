"""Configuración central de Alina. Cambia aquí modelos, idioma y proveedor."""
import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).parent
load_dotenv(RAIZ / ".env")

# --- STT: faster-whisper ---
WHISPER_MODELO = "small"     # tiny, base, small, medium, large-v3-turbo
WHISPER_DEVICE = "cpu"       # "cuda" para usar la GPU
WHISPER_COMPUTE = "int8"     # int8 es lo más estable en la GTX 1650
IDIOMA = None                # None = detección automática; o "es" / "en"
MIC_DEVICE_INDEX = None      # None = micrófono predeterminado
ESPERA_MAX = 10              # segundos esperando a que empieces a hablar
DURACION_MAX = 15            # segundos máximos por frase

# --- LLM ---
LLM_PROVEEDOR = "ollama"     # "ollama" (local) o "claude" (online)
OLLAMA_MODELO = "llama3.2:3b"
CLAUDE_MODELO = "claude-haiku-4-5"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MAX_TOKENS = 300             # respuestas cortas: es una conversación hablada
MAX_HISTORIAL = 20           # mensajes que se conservan (debe ser par)

# --- TTS ---
TTS_PROVEEDOR = "espeak"     # "espeak" (local, robótica) o "fish" (Fish Audio, online)
ESPEAK_VOZ = "es"
ESPEAK_VELOCIDAD = 170

FISH_API_KEY = os.getenv("FISH_API_KEY")
FISH_VOZ_ID = ""             # el ID que aparece en la URL: fish.audio/m/<ID>
FISH_VELOCIDAD = 1.0
FISH_MODELO = None           # None = modelo predeterminado; o p. ej. "s2.1-pro"

# --- Personalidad ---
PERSONA_ARCHIVO = RAIZ / "persona" / "alina.md"
