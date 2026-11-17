import anthropic

from .base import LLM, LlamadaHerramienta, RespuestaLLM


class ClaudeLLM(LLM):
    def __init__(self, modelo: str, api_key: str | None, max_tokens: int):
        if not api_key:
            raise ValueError("Falta ANTHROPIC_API_KEY en el archivo .env")
        self.cliente = anthropic.Anthropic(api_key=api_key)
        self.modelo = modelo
        self.max_tokens = max_tokens

    @staticmethod
    def _traducir(mensajes: list[dict]) -> list[dict]:
        """Claude exige que los resultados de herramientas vayan dentro de un
        mensaje de usuario, agrupados si hay varios seguidos."""
        salida: list[dict] = []
        for m in mensajes:
            if m["role"] == "herramienta":
                bloque = {"type": "tool_result", "tool_use_id": m["id"], "content": m["content"]}
                previo = salida[-1] if salida else None
                if previo and previo["role"] == "user" and isinstance(previo["content"], list):
                    previo["content"].append(bloque)
                else:
                    salida.append({"role": "user", "content": [bloque]})
            elif m["role"] == "assistant" and m.get("llamadas"):
                bloques = [{"type": "text", "text": m["content"]}] if m.get("content") else []
                bloques += [
                    {"type": "tool_use", "id": ll.id, "name": ll.nombre, "input": ll.argumentos}
                    for ll in m["llamadas"]
                ]
                salida.append({"role": "assistant", "content": bloques})
            else:
                salida.append({"role": m["role"], "content": m["content"]})
        return salida

    def responder(self, sistema, mensajes, herramientas=None) -> RespuestaLLM:
        extra = {}
        if herramientas:
            extra["tools"] = [
                {"name": h["nombre"], "description": h["descripcion"], "input_schema": h["parametros"]}
                for h in herramientas
            ]
        r = self.cliente.messages.create(
            model=self.modelo,
            max_tokens=self.max_tokens,
            system=sistema,
            messages=self._traducir(mensajes),
            **extra,
        )
        texto = "".join(b.text for b in r.content if b.type == "text").strip()
        llamadas = [
            LlamadaHerramienta(id=b.id, nombre=b.name, argumentos=dict(b.input))
            for b in r.content
            if b.type == "tool_use"
        ]
        return RespuestaLLM(texto=texto, llamadas=llamadas)
