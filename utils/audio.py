import os
from contextlib import contextmanager


@contextmanager
def silenciar_stderr():
    """Oculta los mensajes de ALSA/JACK que se escriben directo al fd 2."""
    devnull = os.open(os.devnull, os.O_WRONLY)
    original = os.dup(2)
    os.dup2(devnull, 2)
    try:
        yield
    finally:
        os.dup2(original, 2)
        os.close(devnull)
        os.close(original)
