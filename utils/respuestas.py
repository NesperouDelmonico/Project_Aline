"""Interpretación de respuestas habladas de sí / no."""
import re
import unicodedata

NEGATIVAS = {"no", "nop", "cancela", "cancelar", "espera", "detente", "mejor no",
             "nope", "don't", "dont", "stop", "cancel", "wait"}
AFIRMATIVAS = {"si", "claro", "dale", "hazlo", "adelante", "ok", "okay", "vale", "listo",
               "de acuerdo", "confirmo", "correcto", "por favor", "yes", "yeah", "yep",
               "sure", "go ahead", "do it", "please"}


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " " + re.sub(r"[^\w' ]+", " ", texto).strip() + " "


def es_afirmativa(texto: str | None) -> bool:
    """Ante la duda, devuelve False: es más seguro no editar un archivo."""
    if not texto:
        return False
    t = _normalizar(texto)
    if any(f" {p} " in t for p in NEGATIVAS):
        return False
    return any(f" {p} " in t for p in AFIRMATIVAS)
