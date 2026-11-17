"""Bucle principal de Aline: escuchar → pensar (y actuar) → hablar."""
import config
from agente import Agente
from llm import crear_llm
from stt import Oido
from tts import crear_tts
from utils.respuestas import es_afirmativa

DESPEDIDAS = ("adiós", "adios", "chao", "hasta luego", "goodbye", "bye")


def construir_sistema(catalogo_skills: str) -> str:
    partes = [config.PERSONA_ARCHIVO.read_text(encoding="utf-8")]
    if config.HERRAMIENTAS_ACTIVAS:
        partes.append(config.REGLAS_HERRAMIENTAS.read_text(encoding="utf-8"))
        if catalogo_skills:
            partes.append(catalogo_skills)
    return "\n\n".join(partes)


def main():
    oido = Oido()
    cerebro = crear_llm()
    voz = crear_tts()

    def decir(texto: str) -> None:
        print(f"Aline: {texto}")
        try:
            voz.hablar(texto)
        except Exception as e:
            print(f"Error de voz: {e}")

    def avisar(texto: str) -> None:
        if config.AVISOS_POR_VOZ:
            decir(texto)
        else:
            print(f"Aline: {texto}")

    def confirmar(pregunta: str) -> bool:
        decir(pregunta)
        return es_afirmativa(oido.escuchar())

    if config.HERRAMIENTAS_ACTIVAS:
        from herramientas import crear_herramientas
        herramientas, catalogo_skills = crear_herramientas()
    else:
        herramientas, catalogo_skills = {}, ""

    agente = Agente(
        llm=cerebro,
        herramientas=herramientas,
        sistema=construir_sistema(catalogo_skills),
        max_pasos=config.AGENTE_MAX_PASOS,
        max_historial=config.MAX_HISTORIAL,
        max_resultado=config.MAX_RESULTADO,
        avisar=avisar,
        confirmar=confirmar,
    )

    print(
        f"Aline lista (LLM: {config.LLM_PROVEEDOR}, voz: {config.TTS_PROVEEDOR}, "
        f"herramientas: {len(herramientas)}). Di 'adiós' para salir.\n"
    )

    while True:
        texto = oido.escuchar()
        if not texto:
            continue
        try:
            respuesta = agente.procesar(texto, oido.ultimo_idioma)
        except Exception as e:
            print(f"Error del LLM: {e}")
            continue
        decir(respuesta)

        if any(p in texto.lower() for p in DESPEDIDAS):
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nHasta luego.")
