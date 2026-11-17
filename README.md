# Aline

Asistente por voz que corre en local: escucha con faster-whisper, piensa con un LLM
(Ollama en local o Claude en línea), actúa con herramientas y habla con Fish Audio.

## Estructura

```
main.py            bucle escuchar → pensar/actuar → hablar
agente.py          bucle de agente: el modelo decide si responder o usar herramientas
config.py          toda la configuración
stt/               oído (micrófono + Whisper)
llm/               cerebro: interfaz común + Ollama + Claude
tts/               voz: Fish Audio o espeak
herramientas/      acciones que Aline puede ejecutar
skills/            instrucciones de "cómo hacer bien" cada tipo de tarea
persona/           personalidad y reglas de uso de herramientas
tests/             pruebas sin micrófono ni modelo real
```

## Herramientas de archivos

Aline puede buscar, listar, leer (txt, md, docx, pdf, código), crear (docx, txt, md)
y editar archivos dentro de la carpeta personal.

- Las carpetas y archivos ocultos (`.ssh`, `.config`, `.env`...) están bloqueados.
- Antes de editar un archivo existente pregunta por voz y guarda una copia en
  `~/.aline/respaldos`.
- No puede borrar archivos.

## Añadir una habilidad

1. Crea una clase que herede de `Herramienta` en `herramientas/`.
2. Regístrala en `herramientas/__init__.py`.
3. Si la tarea tiene trucos, escribe `skills/<nombre>/SKILL.md` con `name` y `description`.

## Configuración

Copia `.env.example` como `.env` y completa `FISH_API_KEY` y `FISH_VOZ_ID`
(y `ANTHROPIC_API_KEY` si usas Claude).

## Pruebas

```bash
python -m pytest -q
```
