import anthropic

from .base import LLM


class ClaudeLLM(LLM):
    def __init__(self, modelo: str, api_key: str | None, max_tokens: int):
        if not api_key:
            raise ValueError("Falta ANTHROPIC_API_KEY en el archivo .env")
        self.cliente = anthropic.Anthropic(api_key=api_key)
        self.modelo = modelo
        self.max_tokens = max_tokens

    def responder(self, sistema: str, historial: list[dict]) -> str:
        r = self.cliente.messages.create(
            model=self.modelo,
            max_tokens=self.max_tokens,
            system=sistema,
            messages=historial,
        )
        return "".join(b.text for b in r.content if b.type == "text").strip()
