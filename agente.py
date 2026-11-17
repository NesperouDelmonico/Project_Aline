"""El agente: un bucle en el que el modelo decide si responder o usar herramientas.

    usuario → modelo → ¿pide herramientas? ── no ──→ respuesta final
                 ↑            │ sí
                 └── resultado ← ejecutar (con aviso y, si hace falta, confirmación)
"""
import json
import re
import unicodedata
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

# Los modelos pequeños a veces anuncian la acción ("voy a buscar en tu carpeta…")
# en lugar de llamar a la herramienta. Si eso pasa, se les recuerda una vez.
INTENCION = re.compile(
    r"\b(voy a|vamos a|dejame|deja que|usando|utilizando|usare|utilizare|buscare|revisare|"
    r"leere|creare|let me|i will|i'll|i am going to|using)\b"
)
OBJETO = re.compile(
    r"\b(carpeta|carpetas|archivo|archivos|documento|documentos|descargas|escritorio|"
    r"folder|folders|file|files|document|documents|downloads|desktop)\b"
)
RECORDATORIO = (
    "[Aviso del sistema: no ejecutaste ninguna herramienta. Si la tarea la necesita, "
    "llámala ahora mismo sin anunciarlo. Si no la necesita, responde normalmente.]"
)


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[_\-]+", " ", texto)


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
        recordado = False   # el recordatorio se da como máximo una vez por turno
        actuo = False       # si ya usó alguna herramienta, su texto es el resumen final
        for _ in range(self.max_pasos):
            r = self.llm.responder(self.sistema, mensajes, self.esquemas)
            if not r.llamadas:
                if self.esquemas and not (recordado or actuo) and self._anuncia_accion(r.texto):
                    print(f"   ↻ anunció sin actuar: «{r.texto[:80]}»")
                    mensajes += [
                        {"role": "assistant", "content": r.texto},
                        {"role": "user", "content": RECORDATORIO},
                    ]
                    recordado = True
                    continue
                final = r.texto
                break
            actuo = True
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

    def _anuncia_accion(self, texto: str) -> bool:
        """¿El texto promete una acción con archivos que no se ejecutó?"""
        t = _normalizar(texto or "")
        if any(_normalizar(nombre) in t for nombre in self.herramientas):
            return True
        return bool(INTENCION.search(t) and OBJETO.search(t))

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
