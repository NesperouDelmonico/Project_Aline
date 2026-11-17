import json
import re
import uuid

import ollama

from .base import LLM, LlamadaHerramienta, RespuestaLLM

# Algunos modelos pequeños escriben la llamada como texto en lugar de usar el
# canal de herramientas, por ejemplo:  <tool_call>{"name": "...", "arguments": {...}}</tool_call>
PATRON_TOOL_CALL = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.S)


class OllamaLLM(LLM):
    def __init__(self, modelo: str, max_tokens: int, num_ctx: int,
                 temperatura: float = 0.3, pensar: bool | None = None):
        self.modelo = modelo
        self.max_tokens = max_tokens
        self.num_ctx = num_ctx
        self.temperatura = temperatura
        self.pensar = pensar

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

    @staticmethod
    def rescatar_llamadas(texto: str, nombres: set[str]) -> tuple[str, list[LlamadaHerramienta]]:
        """Convierte en llamadas reales las que el modelo escribió como texto."""
        candidatos = PATRON_TOOL_CALL.findall(texto)
        limpio = PATRON_TOOL_CALL.sub("", texto).strip()
        if not candidatos and texto.strip().startswith("{"):
            candidatos, limpio = [texto.strip()], ""
        llamadas = []
        for bruto in candidatos:
            try:
                datos = json.loads(bruto)
            except json.JSONDecodeError:
                continue
            nombre = datos.get("name") or datos.get("function", {}).get("name")
            args = datos.get("arguments") or datos.get("parameters") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            if nombre in nombres and isinstance(args, dict):
                llamadas.append(LlamadaHerramienta(uuid.uuid4().hex[:8], nombre, args))
        return (limpio, llamadas) if llamadas else (texto, [])

    def responder(self, sistema, mensajes, herramientas=None) -> RespuestaLLM:
        extra = {"think": self.pensar} if self.pensar is not None else {}
        r = ollama.chat(
            model=self.modelo,
            messages=[{"role": "system", "content": sistema}, *self._traducir(mensajes)],
            tools=self._esquemas(herramientas) if herramientas else None,
            options={
                "num_predict": self.max_tokens,
                "num_ctx": self.num_ctx,
                "temperature": self.temperatura,
            },
            **extra,
        )
        texto = (r.message.content or "").strip()
        llamadas = [
            # Ollama no asigna identificadores; los generamos para el historial
            LlamadaHerramienta(
                id=uuid.uuid4().hex[:8],
                nombre=tc.function.name,
                argumentos=dict(tc.function.arguments or {}),
            )
            for tc in (r.message.tool_calls or [])
        ]
        if not llamadas and herramientas:
            texto, llamadas = self.rescatar_llamadas(texto, {h["nombre"] for h in herramientas})
        return RespuestaLLM(texto=texto, llamadas=llamadas)
