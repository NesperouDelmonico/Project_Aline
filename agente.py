"""El agente: un bucle en el que el modelo decide si responder o usar herramientas.

    usuario → modelo → ¿pide herramientas? ── no ──→ respuesta final
                 ↑            │ sí
                 └── resultado ← ejecutar (con aviso y, si hace falta, confirmación)
"""
import json
from collections.abc import Callable

from herramientas import ErrorHerramienta, Herramienta
from llm import LLM, LlamadaHerramienta

# La instrucción de idioma va pegada al mensaje y escrita en ese idioma:
# los modelos pequeños la respetan mucho mejor que si va en el prompt de sistema.
INSTRUCCION_IDIOMA = {
    "es": "Responde únicamente en español.",
    "en": "Reply only in English.",
    "pt": "Responda apenas em português.",
    "fr": "Réponds uniquement en français.",
    "ja": "日本語だけで答えてください。",
}

MENSAJES = {
    "cancelado": "El usuario canceló esta acción. No la repitas a menos que lo pida de nuevo.",
    "sin_pasos": {
        "es": "No alcancé a terminar la tarea. ¿Quieres que lo intente de otra forma?",
        "en": "I couldn't finish the task. Do you want me to try another way?",
    },
    "vacio": {
        "es": "Listo.",
        "en": "Done.",
    },
}


class Agente:
    def __init__(
        self,
        llm: LLM,
        herramientas: dict[str, Herramienta],
        sistema: str,
        max_pasos: int,
        max_historial: int,
        max_resultado: int,
        avisar: Callable[[str], None],
        confirmar: Callable[[str], bool],
    ):
        self.llm = llm
        self.herramientas = herramientas
        self.esquemas = [h.esquema() for h in herramientas.values()] or None
        self.sistema = sistema
        self.max_pasos = max_pasos
        self.max_historial = max_historial
        self.max_resultado = max_resultado
        self.avisar = avisar
        self.confirmar = confirmar
        # Solo se conserva la conversación (preguntas y respuestas finales);
        # los pasos intermedios con herramientas se descartan al terminar
        # cada turno para no llenar el contexto del modelo.
        self.historial: list[dict] = []

    def procesar(self, texto: str, idioma: str | None) -> str:
        idioma = idioma or "es"
        nota = INSTRUCCION_IDIOMA.get(idioma)
        contenido = f"{texto}\n\n[{nota}]" if nota else texto
        mensajes = [*self.historial, {"role": "user", "content": contenido}]

        final = None
        for _ in range(self.max_pasos):
            r = self.llm.responder(self.sistema, mensajes, self.esquemas)
            if not r.llamadas:
                final = r.texto
                break
            mensajes.append({"role": "assistant", "content": r.texto, "llamadas": r.llamadas})
            for llamada in r.llamadas:
                resultado = self._ejecutar(llamada, idioma)
                mensajes.append({
                    "role": "herramienta", "id": llamada.id,
                    "nombre": llamada.nombre, "content": resultado,
                })
        if final is None:
            final = MENSAJES["sin_pasos"].get(idioma, MENSAJES["sin_pasos"]["es"])
        elif not final:
            final = MENSAJES["vacio"].get(idioma, MENSAJES["vacio"]["es"])

        self.historial += [{"role": "user", "content": texto}, {"role": "assistant", "content": final}]
        self.historial = self.historial[-self.max_historial:]
        return final

    def _ejecutar(self, llamada: LlamadaHerramienta, idioma: str) -> str:
        herramienta = self.herramientas.get(llamada.nombre)
        if herramienta is None:
            return f"Error: no existe la herramienta '{llamada.nombre}'."
        try:
            args = herramienta.filtrar_argumentos(llamada.argumentos)
        except ErrorHerramienta as e:
            return f"Error: {e}"

        print(f"🔧 {llamada.nombre}({json.dumps(args, ensure_ascii=False)[:150]})")

        if herramienta.requiere_confirmacion:
            pregunta = herramienta.texto_confirmacion(args, idioma) or "¿Continúo?"
            if not self.confirmar(pregunta):
                print("   ✋ cancelado por el usuario")
                return MENSAJES["cancelado"]
        else:
            aviso = herramienta.texto_aviso(args, idioma)
            if aviso:
                self.avisar(aviso)

        try:
            resultado = herramienta.ejecutar(**args)
        except ErrorHerramienta as e:
            resultado = f"Error: {e}"
        except Exception as e:  # un fallo inesperado no debe tumbar a Aline
            resultado = f"Error inesperado ({type(e).__name__}): {e}"

        print(f"   → {resultado[:120].replace(chr(10), ' | ')}")
        if len(resultado) > self.max_resultado:
            resultado = resultado[: self.max_resultado] + "\n[... recortado]"
        return resultado
