import ollama

from .base import LLM


class OllamaLLM(LLM):
    def __init__(self, modelo: str, max_tokens: int):
        self.modelo = modelo
        self.max_tokens = max_tokens

    def responder(self, sistema: str, historial: list[dict]) -> str:
        mensajes = [{"role": "system", "content": sistema}, *historial]
        r = ollama.chat(
            model=self.modelo,
            messages=mensajes,
            options={"num_predict": self.max_tokens},
        )
        return r["message"]["content"].strip()
