"""Zona de archivos a la que Aline tiene acceso.

Reglas:
- Todo debe estar dentro de la carpeta raíz (por defecto, la carpeta personal).
- Las carpetas y archivos ocultos (que empiezan por ".") están prohibidos:
  ahí viven claves SSH, contraseñas del navegador, configuraciones y el .env.
- Los enlaces simbólicos que apunten fuera de la raíz se rechazan.
- Como los nombres llegan por voz, cada parte de la ruta se busca de forma
  aproximada ("documentos" encuentra "Documentos" o "Documents").
"""
import difflib
import os
import re
import time
import unicodedata
from collections.abc import Iterator
from pathlib import Path

from .base import ErrorHerramienta

# Nombres en español e inglés de las carpetas típicas del usuario
SINONIMOS = {
    "documentos": "documents", "descargas": "downloads", "escritorio": "desktop",
    "imagenes": "pictures", "fotos": "pictures", "musica": "music", "videos": "videos",
    "plantillas": "templates", "publico": "public",
}
SINONIMOS |= {v: k for k, v in SINONIMOS.items()}


def normalizar(texto: str) -> str:
    """minúsculas, sin tildes y con separadores (_ - .) convertidos en espacios."""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c)).lower()
    return re.sub(r"[\s_\-\.]+", " ", texto).strip()


class Espacio:
    def __init__(self, raiz: Path, excluidas: set[str], max_archivos: int = 200_000, max_segundos: float = 8.0):
        self.raiz = raiz.expanduser().resolve()
        self.excluidas = {e.lower() for e in excluidas}
        self.max_archivos = max_archivos
        self.max_segundos = max_segundos

    # ---------- validación ----------
    def _nombre_permitido(self, nombre: str) -> bool:
        return not nombre.startswith(".") and nombre.lower() not in self.excluidas

    def _dentro(self, ruta: Path) -> Path:
        real = ruta.resolve()
        if real != self.raiz and not real.is_relative_to(self.raiz):
            raise ErrorHerramienta("Esa ruta está fuera de la carpeta permitida.")
        for parte in real.relative_to(self.raiz).parts:
            if not self._nombre_permitido(parte):
                raise ErrorHerramienta(f"'{parte}' es una carpeta o archivo protegido.")
        return real

    def relativa(self, ruta: Path) -> str:
        rel = ruta.resolve().relative_to(self.raiz)
        return str(rel) if str(rel) != "." else "(carpeta personal)"

    # ---------- resolución de rutas dichas por voz ----------
    def _limpiar(self, texto: str) -> str:
        t = (texto or "").strip().strip("\"'").strip()
        if t.startswith("~"):
            t = t[1:]
        raiz = str(self.raiz)
        if t.startswith(raiz):
            t = t[len(raiz):]
        elif t.startswith("/home/"):
            # p. ej. /home/nesp/... dicho con otro nombre de usuario
            partes = Path(t).parts
            t = str(Path(*partes[3:])) if len(partes) > 3 else ""
        elif t.startswith("/"):
            raise ErrorHerramienta("Esa ruta está fuera de la carpeta permitida.")
        return t.strip("/")

    def _buscar_hijo(self, carpeta: Path, nombre: str) -> Path | None:
        exacto = carpeta / nombre
        if exacto.exists():
            return exacto
        objetivo = normalizar(nombre)
        candidatos = {}
        try:
            for hijo in carpeta.iterdir():
                if self._nombre_permitido(hijo.name):
                    candidatos[normalizar(hijo.name)] = hijo
                    candidatos.setdefault(normalizar(hijo.stem), hijo)
        except (PermissionError, NotADirectoryError):
            return None
        if objetivo in candidatos:
            return candidatos[objetivo]
        if SINONIMOS.get(objetivo) in candidatos:
            return candidatos[SINONIMOS[objetivo]]
        cercanos = difflib.get_close_matches(objetivo, list(candidatos), n=1, cutoff=0.75)
        return candidatos[cercanos[0]] if cercanos else None

    def resolver(self, texto: str, debe_existir: bool = True) -> Path:
        """Convierte una ruta dicha por el usuario en una ruta real y segura."""
        partes = [p for p in self._limpiar(texto).split("/") if p and p != "."]
        if any(p == ".." for p in partes):
            raise ErrorHerramienta("No se permiten rutas con '..'.")
        actual = self.raiz
        for i, parte in enumerate(partes):
            es_ultima = i == len(partes) - 1
            hijo = self._buscar_hijo(actual, parte)
            if hijo is None:
                if es_ultima and not debe_existir:
                    hijo = actual / parte
                else:
                    raise ErrorHerramienta(
                        f"No encontré '{parte}' dentro de {self.relativa(actual)}."
                    )
            actual = hijo
        return self._dentro(actual)

    # ---------- recorrido ----------
    def recorrer(self, carpeta: Path) -> Iterator[Path]:
        """Recorre archivos y carpetas visibles, con límites de cantidad y tiempo
        para no quedarse colgado en carpetas enormes."""
        inicio, contador = time.monotonic(), 0
        for actual, dirs, archivos in os.walk(carpeta, followlinks=False):
            dirs[:] = [d for d in dirs if self._nombre_permitido(d)]
            for nombre in dirs + [a for a in archivos if self._nombre_permitido(a)]:
                contador += 1
                if contador > self.max_archivos or time.monotonic() - inicio > self.max_segundos:
                    return
                yield Path(actual) / nombre
