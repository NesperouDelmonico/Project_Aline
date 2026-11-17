"""Configuración central de Aline. Cambia aquí modelos, idioma y proveedor."""
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
OLLAMA_MODELO = "qwen2.5:3b"
OLLAMA_NUM_CTX = 8192        # contexto; con la GTX 1650 no conviene pasar de 8192
CLAUDE_MODELO = "claude-haiku-4-5"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MAX_TOKENS = 1500            # alto para que pueda escribir documentos; la voz sigue breve
MAX_HISTORIAL = 20           # mensajes de conversación que se conservan (debe ser par)

# --- Agente y herramientas ---
HERRAMIENTAS_ACTIVAS = True  # False = Aline solo conversa
AGENTE_MAX_PASOS = 6         # máximo de rondas modelo → herramienta por petición
AVISOS_POR_VOZ = True        # decir "Buscando…", "Leyendo…" mientras trabaja
MAX_RESULTADO = 3500         # caracteres máximos que una herramienta le devuelve al modelo

CARPETA_PERMITIDA = Path.home()          # Aline solo accede a lo que hay aquí dentro
CARPETAS_EXCLUIDAS = {                   # además de todo lo oculto (empieza por ".")
    "node_modules", "__pycache__", "venv", "site-packages", "snap",
}
CARPETA_RESPALDOS = Path.home() / ".aline" / "respaldos"   # oculta: Aline no puede tocarla
TAM_PARTE_LECTURA = 3000                 # caracteres por parte al leer archivos largos
CARPETA_SKILLS = RAIZ / "skills"

# --- TTS ---
TTS_PROVEEDOR = "fish"       # "fish" (Fish Audio, online) o "espeak" (local, robótica)
ESPEAK_VOZ = "es"
ESPEAK_VELOCIDAD = 170

FISH_API_KEY = os.getenv("FISH_API_KEY")
FISH_VOZ_ID = os.getenv("FISH_VOZ_ID", "")  # el ID de la URL: fish.audio/m/<ID>
FISH_VELOCIDAD = 1.0
FISH_MODELO = None           # None = modelo predeterminado; o p. ej. "s2.1-pro"

# --- Personalidad ---
PERSONA_ARCHIVO = RAIZ / "persona" / "aline.md"
REGLAS_HERRAMIENTAS = RAIZ / "persona" / "herramientas.md"
