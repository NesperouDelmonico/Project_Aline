"""Herramientas de archivos: buscar, listar, leer, crear y editar."""
import difflib
import shutil
from datetime import datetime
from pathlib import Path

from . import formatos
from .base import ErrorHerramienta, Herramienta
from .espacio import Espacio, normalizar

RUTA_DESC = (
    "Ruta relativa a la carpeta personal del usuario, por ejemplo "
    "'Documentos/universidad/informe.docx'. Se aceptan nombres aproximados."
)


def _fecha(ruta: Path) -> str:
    return datetime.fromtimestamp(ruta.stat().st_mtime).strftime("%Y-%m-%d")


class _ConEspacio(Herramienta):
    def __init__(self, espacio: Espacio):
        self.espacio = espacio


class BuscarArchivos(_ConEspacio):
    nombre = "buscar_archivos"
    descripcion = (
        "Busca archivos o carpetas por nombre aproximado dentro de la carpeta personal. "
        "Úsala cuando el usuario no da la ruta exacta."
    )
    parametros = {
        "type": "object",
        "properties": {
            "consulta": {"type": "string", "description": "Palabras del nombre, p. ej. 'informe operaciones'"},
            "carpeta": {"type": "string", "description": "Carpeta donde buscar; vacío = toda la carpeta personal"},
            "extension": {"type": "string", "description": "Filtrar por extensión, p. ej. 'docx' (opcional)"},
        },
        "required": ["consulta"],
    }
    aviso = {"es": "Buscando {consulta}.", "en": "Searching for {consulta}."}
    MAX_RESULTADOS = 6

    @staticmethod
    def _puntaje(tokens: list[str], nombre: str, carpeta: str) -> float:
        palabras_nombre, palabras_carpeta = nombre.split(), carpeta.split()
        acierto = 0.0
        for t in tokens:
            if t in nombre or difflib.get_close_matches(t, palabras_nombre, n=1, cutoff=0.8):
                acierto += 1
            elif t in carpeta or difflib.get_close_matches(t, palabras_carpeta, n=1, cutoff=0.8):
                acierto += 0.5
        parecido = difflib.SequenceMatcher(None, " ".join(tokens), nombre).ratio()
        return 0.75 * acierto / len(tokens) + 0.25 * parecido

    def ejecutar(self, consulta: str, carpeta: str = "", extension: str = "") -> str:
        base = self.espacio.resolver(carpeta)
        if not base.is_dir():
            raise ErrorHerramienta(f"{self.espacio.relativa(base)} no es una carpeta.")
        tokens = normalizar(consulta).split()
        if not tokens:
            raise ErrorHerramienta("La consulta está vacía.")
        ext = "." + extension.lower().lstrip(".") if extension else ""

        encontrados = []
        for ruta in self.espacio.recorrer(base):
            if ext and ruta.suffix.lower() != ext:
                continue
            rel = ruta.relative_to(self.espacio.raiz)
            nombre = normalizar(ruta.stem if ruta.is_file() else ruta.name)
            puntaje = self._puntaje(tokens, nombre, normalizar(str(rel.parent)))
            if puntaje >= 0.45:
                encontrados.append((puntaje, ruta.stat().st_mtime, ruta))

        if not encontrados:
            return f"No encontré nada que coincida con '{consulta}' en {self.espacio.relativa(base)}."
        encontrados.sort(key=lambda x: (x[0], x[1]), reverse=True)
        lineas = []
        for i, (_, _, ruta) in enumerate(encontrados[: self.MAX_RESULTADOS], 1):
            tipo = "carpeta" if ruta.is_dir() else f"modificado {_fecha(ruta)}"
            lineas.append(f"{i}. {self.espacio.relativa(ruta)} ({tipo})")
        extra = len(encontrados) - self.MAX_RESULTADOS
        if extra > 0:
            lineas.append(f"... y {extra} coincidencias más.")
        return "Resultados:\n" + "\n".join(lineas)


class ListarCarpeta(_ConEspacio):
    nombre = "listar_carpeta"
    descripcion = "Muestra qué archivos y carpetas hay dentro de una carpeta."
    parametros = {
        "type": "object",
        "properties": {"carpeta": {"type": "string", "description": RUTA_DESC + " Vacío = carpeta personal."}},
        "required": [],
    }
    aviso = {"es": "Revisando la carpeta.", "en": "Checking the folder."}
    MAX = 40

    def ejecutar(self, carpeta: str = "") -> str:
        base = self.espacio.resolver(carpeta)
        if not base.is_dir():
            raise ErrorHerramienta(f"{self.espacio.relativa(base)} no es una carpeta.")
        hijos = [h for h in base.iterdir() if not h.name.startswith(".")]
        hijos.sort(key=lambda h: (not h.is_dir(), h.name.lower()))
        if not hijos:
            return f"{self.espacio.relativa(base)} está vacía."
        lineas = [f"{h.name}/" if h.is_dir() else h.name for h in hijos[: self.MAX]]
        if len(hijos) > self.MAX:
            lineas.append(f"... y {len(hijos) - self.MAX} elementos más.")
        return f"Contenido de {self.espacio.relativa(base)}:\n" + "\n".join(lineas)


class LeerArchivo(_ConEspacio):
    nombre = "leer_archivo"
    descripcion = (
        "Lee el texto de un archivo (txt, md, docx, pdf, código...). Los archivos largos "
        "se entregan por partes: pide la siguiente con el parámetro 'parte'."
    )
    parametros = {
        "type": "object",
        "properties": {
            "ruta": {"type": "string", "description": RUTA_DESC},
            "parte": {"type": "integer", "description": "Número de parte, empieza en 1"},
        },
        "required": ["ruta"],
    }
    aviso = {"es": "Leyendo el archivo.", "en": "Reading the file."}

    def __init__(self, espacio: Espacio, tam_parte: int):
        super().__init__(espacio)
        self.tam_parte = tam_parte

    def ejecutar(self, ruta: str, parte: int = 1) -> str:
        archivo = self.espacio.resolver(ruta)
        if not archivo.is_file():
            raise ErrorHerramienta(f"{self.espacio.relativa(archivo)} no es un archivo.")
        texto = formatos.extraer_texto(archivo).strip()
        if not texto:
            return f"{self.espacio.relativa(archivo)} está vacío."
        partes = [texto[i : i + self.tam_parte] for i in range(0, len(texto), self.tam_parte)]
        parte = max(1, min(int(parte), len(partes)))
        return (
            f"Archivo: {self.espacio.relativa(archivo)} | Parte {parte} de {len(partes)}\n\n"
            f"{partes[parte - 1]}"
        )


class CrearArchivo(_ConEspacio):
    nombre = "crear_archivo"
    descripcion = (
        "Crea un archivo nuevo (.docx, .txt o .md) con el contenido indicado. No sobrescribe. "
        "En el contenido usa '# ' para títulos, '## ' para subtítulos y '- ' para viñetas."
    )
    parametros = {
        "type": "object",
        "properties": {
            "ruta": {"type": "string", "description": RUTA_DESC + " Sin extensión se crea .docx."},
            "contenido": {"type": "string", "description": "Texto completo del archivo"},
        },
        "required": ["ruta", "contenido"],
    }
    aviso = {"es": "Creando el archivo.", "en": "Creating the file."}

    def ejecutar(self, ruta: str, contenido: str) -> str:
        destino = self.espacio.resolver(ruta, debe_existir=False)
        if not destino.suffix:
            destino = destino.with_suffix(".docx")
        if destino.exists():
            raise ErrorHerramienta(
                f"{self.espacio.relativa(destino)} ya existe. Usa editar_archivo o elige otro nombre."
            )
        if not destino.parent.is_dir():
            raise ErrorHerramienta(f"La carpeta {self.espacio.relativa(destino.parent)} no existe.")
        formatos.crear(destino, contenido)
        return f"Creado: {self.espacio.relativa(destino)}"


class _Edicion(_ConEspacio):
    """Base de las ediciones: siempre respalda el original antes de tocarlo."""
    requiere_confirmacion = True

    def __init__(self, espacio: Espacio, carpeta_respaldos: Path):
        super().__init__(espacio)
        self.respaldos = carpeta_respaldos

    def _abrir(self, ruta: str) -> Path:
        archivo = self.espacio.resolver(ruta)
        if not archivo.is_file():
            raise ErrorHerramienta(f"{self.espacio.relativa(archivo)} no es un archivo.")
        if archivo.suffix.lower() not in formatos.ESCRIBIBLES | formatos.TEXTO_PLANO:
            raise ErrorHerramienta(f"No puedo editar archivos {archivo.suffix}.")
        return archivo

    def texto_confirmacion(self, args: dict, idioma: str) -> str | None:
        # Se nombra solo el archivo, sin la ruta, para que suene natural
        archivo = Path(str(args.get("ruta", ""))).stem.replace("_", " ")
        return super().texto_confirmacion({**args, "archivo": archivo}, idioma)

    def _respaldar(self, archivo: Path) -> Path:
        self.respaldos.mkdir(parents=True, exist_ok=True)
        marca = datetime.now().strftime("%Y%m%d-%H%M%S")
        copia = self.respaldos / f"{marca}_{archivo.name}"
        shutil.copy2(archivo, copia)
        return copia


class EditarArchivo(_Edicion):
    nombre = "editar_archivo"
    descripcion = (
        "Reemplaza un texto exacto por otro dentro de un archivo existente (.docx, .txt, .md...). "
        "Lee el archivo antes para copiar el texto exacto. Guarda una copia de respaldo."
    )
    parametros = {
        "type": "object",
        "properties": {
            "ruta": {"type": "string", "description": RUTA_DESC},
            "buscar": {"type": "string", "description": "Texto exacto que hay ahora en el archivo"},
            "reemplazar": {"type": "string", "description": "Texto nuevo"},
        },
        "required": ["ruta", "buscar", "reemplazar"],
    }
    aviso = {"es": "Editando el archivo.", "en": "Editing the file."}
    confirmacion = {
        "es": "¿Cambio «{buscar}» por «{reemplazar}» en {archivo}?",
        "en": "Should I change “{buscar}” to “{reemplazar}” in {archivo}?",
    }

    def ejecutar(self, ruta: str, buscar: str, reemplazar: str) -> str:
        archivo = self._abrir(ruta)
        if buscar not in formatos.extraer_texto(archivo):
            raise ErrorHerramienta(
                "No encontré ese texto exacto en el archivo. Léelo y copia el texto tal cual aparece."
            )
        copia = self._respaldar(archivo)
        n = formatos.reemplazar(archivo, buscar, reemplazar)
        return f"Hecho: {n} reemplazo(s) en {self.espacio.relativa(archivo)}. Respaldo: {copia.name}"


class AgregarAlArchivo(_Edicion):
    nombre = "agregar_al_archivo"
    descripcion = (
        "Añade texto al final de un archivo existente. En .docx acepta '# ' para títulos y "
        "'- ' para viñetas. Guarda una copia de respaldo."
    )
    parametros = {
        "type": "object",
        "properties": {
            "ruta": {"type": "string", "description": RUTA_DESC},
            "contenido": {"type": "string", "description": "Texto que se añade al final"},
        },
        "required": ["ruta", "contenido"],
    }
    aviso = {"es": "Añadiendo el texto.", "en": "Adding the text."}
    confirmacion = {
        "es": "¿Añado ese texto al final de {archivo}?",
        "en": "Should I add that text at the end of {archivo}?",
    }

    def ejecutar(self, ruta: str, contenido: str) -> str:
        archivo = self._abrir(ruta)
        copia = self._respaldar(archivo)
        formatos.agregar(archivo, contenido)
        return f"Texto añadido a {self.espacio.relativa(archivo)}. Respaldo: {copia.name}"
