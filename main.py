"""Bucle principal de Alina: escuchar → pensar → hablar."""
import config
from llm import crear_llm
from stt import Oido
from tts import crear_tts

DESPEDIDAS = ("adiós", "adios", "chao", "hasta luego", "goodbye", "bye")
IDIOMAS = {"es": "español", "en": "inglés", "ja": "japonés", "pt": "portugués", "fr": "francés"}


def instruccion_idioma(codigo: str | None) -> str:
    """Instrucción explícita de idioma: los modelos pequeños tienden a imitar
    el idioma del prompt de sistema si no se les dice otra cosa."""
    if not codigo:
        return ""
    nombre = IDIOMAS.get(codigo, codigo)
    return (
        f"\n\nIdioma detectado en el último mensaje del usuario: {nombre}. "
        f"Responde en {nombre}, a menos que el usuario te pida explícitamente otro idioma."
    )


def main():
    persona = config.PERSONA_ARCHIVO.read_text(encoding="utf-8")
    oido = Oido()
    cerebro = crear_llm()
    voz = crear_tts()
    historial: list[dict] = []

    print(f"Alina lista (LLM: {config.LLM_PROVEEDOR}, voz: {config.TTS_PROVEEDOR}). Di 'adiós' para salir.\n")

    while True:
        texto = oido.escuchar()
        if not texto:
            continue

        historial.append({"role": "user", "content": texto})
        try:
            sistema = persona + instruccion_idioma(oido.ultimo_idioma)
            respuesta = cerebro.responder(sistema, historial)
        except Exception as e:
            print(f"Error del LLM: {e}")
            historial.pop()
            continue

        historial.append({"role": "assistant", "content": respuesta})
        historial = historial[-config.MAX_HISTORIAL:]
        print(f"Alina: {respuesta}")
        try:
            voz.hablar(respuesta)
        except Exception as e:
            print(f"Error de voz: {e}")

        if any(p in texto.lower() for p in DESPEDIDAS):
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nHasta luego.")
