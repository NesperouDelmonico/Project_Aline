import uuid

import ollama

from .base import LLM, LlamadaHerramienta, RespuestaLLM


class OllamaLLM(LLM):
    def __init__(self, modelo: str, max_tokens: int, num_ctx: int):
        self.modelo = modelo
        self.max_tokens = max_tokens
        self.num_ctx = num_ctx

    @staticmethod
    def _traducir(mensajes: list[dict]) -> list[dict]:
        salida = []
        for m in mensajes:
            if m["role"] == "herramienta":
                salida.append({"role": "tool", "tool_name": m["nombre"], "content": m["content"]})
            elif m["role"] == "assistant" and m.get("llamadas"):
                salida.append({
                    "role": "assistant",
                    "content": m.get("content", ""),
                    "tool_calls": [
                        {"function": {"name": ll.nombre, "arguments": ll.argumentos}}
                        for ll in m["llamadas"]
                    ],
                })
            else:
                salida.append({"role": m["role"], "content": m["content"]})
        return salida

    @staticmethod
    def _esquemas(herramientas: list[dict]) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": h["nombre"],
                    "description": h["descripcion"],
                    "parameters": h["parametros"],
                },
            }
            for h in herramientas
        ]

    def responder(self, sistema, mensajes, herramientas=None) -> RespuestaLLM:
        r = ollama.chat(
            model=self.modelo,
            messages=[{"role": "system", "content": sistema}, *self._traducir(mensajes)],
            tools=self._esquemas(herramientas) if herramientas else None,
            options={"num_predict": self.max_tokens, "num_ctx": self.num_ctx},
        )
        llamadas = [
            # Ollama no asigna identificadores; los generamos para el historial
            LlamadaHerramienta(
                id=uuid.uuid4().hex[:8],
                nombre=tc.function.name,
                argumentos=dict(tc.function.arguments or {}),
            )
            for tc in (r.message.tool_calls or [])
        ]
        return RespuestaLLM(texto=(r.message.content or "").strip(), llamadas=llamadas)
