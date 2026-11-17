"""Registro de herramientas. Para añadir una habilidad nueva a Aline:
1. Crea una clase que herede de Herramienta (ver base.py).
2. Añádela a la lista de crear_herramientas().
3. Si la tarea tiene "trucos", escribe una skill en skills/<nombre>/SKILL.md.
"""
import config

from .archivos import (
    AgregarAlArchivo, BuscarArchivos, CrearArchivo, EditarArchivo, LeerArchivo, ListarCarpeta,
)
from .base import ErrorHerramienta, Herramienta
from .espacio import Espacio
from .skills import CargarSkill, cargar_skills, catalogo

__all__ = ["ErrorHerramienta", "Herramienta", "crear_herramientas"]


def crear_herramientas() -> tuple[dict[str, Herramienta], str]:
    """Devuelve (herramientas por nombre, catálogo de skills para el prompt)."""
    espacio = Espacio(config.CARPETA_PERMITIDA, config.CARPETAS_EXCLUIDAS)
    lista: list[Herramienta] = [
        BuscarArchivos(espacio),
        ListarCarpeta(espacio),
        LeerArchivo(espacio, config.TAM_PARTE_LECTURA),
        CrearArchivo(espacio),
        EditarArchivo(espacio, config.CARPETA_RESPALDOS),
        AgregarAlArchivo(espacio, config.CARPETA_RESPALDOS),
    ]
    skills = cargar_skills(config.CARPETA_SKILLS)
    if skills:
        lista.append(CargarSkill(skills))
    return {h.nombre: h for h in lista}, catalogo(skills)
