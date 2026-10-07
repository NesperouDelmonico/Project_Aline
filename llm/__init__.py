import config

from .base import LLM


def crear_llm() -> LLM:
    """Devuelve el proveedor elegido en config.py. Los imports son perezosos
    para no exigir instalar librerías de un proveedor que no usas."""
    if config.LLM_PROVEEDOR == "ollama":
        from .ollama_llm import OllamaLLM
        return OllamaLLM(config.OLLAMA_MODELO, config.MAX_TOKENS)
    if config.LLM_PROVEEDOR == "claude":
        from .claude_llm import ClaudeLLM
        return ClaudeLLM(config.CLAUDE_MODELO, config.ANTHROPIC_API_KEY, config.MAX_TOKENS)
    raise ValueError(f"Proveedor desconocido: {config.LLM_PROVEEDOR}")
