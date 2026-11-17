"""Lectura y escritura de los formatos que Aline entiende."""
from pathlib import Path

from .base import ErrorHerramienta

TEXTO_PLANO = {".txt", ".md", ".csv", ".json", ".py", ".js", ".ts", ".html", ".css",
               ".yaml", ".yml", ".xml", ".log", ".ini", ".toml", ".sh", ".tex"}
LEGIBLES = TEXTO_PLANO | {".docx", ".pdf"}
ESCRIBIBLES = {".docx", ".txt", ".md"}
MAX_BYTES_TEXTO = 20 * 1024 * 1024


# ---------- lectura ----------
def extraer_texto(ruta: Path) -> str:
    ext = ruta.suffix.lower()
    if ext in TEXTO_PLANO:
        if ruta.stat().st_size > MAX_BYTES_TEXTO:
            raise ErrorHerramienta("El archivo es demasiado grande para leerlo.")
        return ruta.read_text(encoding="utf-8", errors="replace")
    if ext == ".docx":
        return _texto_docx(ruta)
    if ext == ".pdf":
        return _texto_pdf(ruta)
    raise ErrorHerramienta(
        f"No sé leer archivos {ext or 'sin extensión'}. Puedo leer: {', '.join(sorted(LEGIBLES))}."
    )


def _texto_docx(ruta: Path) -> str:
    from docx import Document

    doc = Document(str(ruta))
    bloques = [p.text for p in doc.paragraphs if p.text.strip()]
    for i, tabla in enumerate(doc.tables, 1):
        bloques.append(f"[Tabla {i}]")
        for fila in tabla.rows:
            bloques.append(" | ".join(c.text.strip() for c in fila.cells))
    return "\n".join(bloques)


def _texto_pdf(ruta: Path) -> str:
    from pypdf import PdfReader

    lector = PdfReader(str(ruta))
    paginas = [f"[Página {i}]\n{(p.extract_text() or '').strip()}" for i, p in enumerate(lector.pages, 1)]
    texto = "\n\n".join(paginas)
    if not texto.replace("[Página", "").strip(" \n0123456789]"):
        raise ErrorHerramienta("El PDF no tiene texto extraíble (probablemente es escaneado).")
    return texto


# ---------- escritura ----------
def _agregar_bloques_docx(doc, contenido: str) -> None:
    """Formato ligero: '# ' título, '## ' subtítulo, '- ' viñeta, línea vacía separa párrafos."""
    for linea in contenido.splitlines():
        t = linea.rstrip()
        if not t.strip():
            continue
        if t.startswith("## "):
            doc.add_heading(t[3:].strip(), level=2)
        elif t.startswith("# "):
            doc.add_heading(t[2:].strip(), level=1)
        elif t.lstrip().startswith(("- ", "* ")):
            doc.add_paragraph(t.lstrip()[2:].strip(), style="List Bullet")
        else:
            doc.add_paragraph(t.strip())


def crear(ruta: Path, contenido: str) -> None:
    ext = ruta.suffix.lower()
    if ext == ".docx":
        from docx import Document

        doc = Document()
        _agregar_bloques_docx(doc, contenido)
        doc.save(str(ruta))
    elif ext in ESCRIBIBLES:
        ruta.write_text(contenido, encoding="utf-8")
    else:
        raise ErrorHerramienta(f"Solo puedo crear: {', '.join(sorted(ESCRIBIBLES))}.")


def agregar(ruta: Path, contenido: str) -> None:
    ext = ruta.suffix.lower()
    if ext == ".docx":
        from docx import Document

        doc = Document(str(ruta))
        _agregar_bloques_docx(doc, contenido)
        doc.save(str(ruta))
    elif ext in TEXTO_PLANO:
        previo = ruta.read_text(encoding="utf-8", errors="replace")
        separador = "" if not previo or previo.endswith("\n") else "\n"
        ruta.write_text(previo + separador + contenido + "\n", encoding="utf-8")
    else:
        raise ErrorHerramienta(f"No puedo editar archivos {ext}.")


def reemplazar(ruta: Path, buscar: str, nuevo: str) -> int:
    """Reemplaza todas las apariciones y devuelve cuántas hubo."""
    ext = ruta.suffix.lower()
    if ext == ".docx":
        return _reemplazar_docx(ruta, buscar, nuevo)
    if ext in TEXTO_PLANO:
        texto = ruta.read_text(encoding="utf-8", errors="replace")
        n = texto.count(buscar)
        if n:
            ruta.write_text(texto.replace(buscar, nuevo), encoding="utf-8")
        return n
    raise ErrorHerramienta(f"No puedo editar archivos {ext}.")


def _parrafos_docx(doc):
    yield from doc.paragraphs
    for tabla in doc.tables:
        for fila in tabla.rows:
            for celda in fila.cells:
                yield from celda.paragraphs


def _reemplazar_docx(ruta: Path, buscar: str, nuevo: str) -> int:
    from docx import Document

    doc = Document(str(ruta))
    total = 0
    for p in _parrafos_docx(doc):
        if buscar not in p.text:
            continue
        # Caso ideal: el texto está entero dentro de un fragmento con formato
        # propio (run); así se conservan negritas, colores, etc.
        hecho = False
        for run in p.runs:
            if buscar in run.text:
                total += run.text.count(buscar)
                run.text = run.text.replace(buscar, nuevo)
                hecho = True
        if not hecho and p.runs:
            # El texto cruza varios fragmentos: se unifica el párrafo con el
            # formato del primero (se pierde el formato mixto de ese párrafo).
            total += p.text.count(buscar)
            texto = p.text.replace(buscar, nuevo)
            p.runs[0].text = texto
            for run in p.runs[1:]:
                run.text = ""
    if total:
        doc.save(str(ruta))
    return total
