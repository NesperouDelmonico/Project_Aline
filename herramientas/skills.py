"""Skills: instrucciones de "cómo hacer bien" un tipo de tarea.

Cada skill es una carpeta dentro de skills/ con un archivo SKILL.md:

    ---
    name: documentos
    description: Una línea que dice cuándo usarla.
    ---
    Instrucciones completas...

El modelo solo ve el nombre y la descripción de cada skill (el catálogo).
Cuando la necesita, carga el texto completo con la herramienta cargar_skill.
Así el contexto, que en un modelo local es pequeño, no se llena de golpe.
"""
from dataclasses import dataclass
from pathlib import Path

from .base import ErrorHerramienta, Herramienta


@dataclass
class Skill:
    nombre: str
    descripcion: str
    instrucciones: str


def _leer_skill(archivo: Path) -> Skill | None:
    texto = archivo.read_text(encoding="utf-8")
    if not texto.startswith("---"):
        return None
    _, cabecera, cuerpo = texto.split("---", 2)
    datos = {}
    for linea in cabecera.strip().splitlines():
        if ":" in linea:
            clave, valor = linea.split(":", 1)
            datos[clave.strip()] = valor.strip()
    nombre = datos.get("name") or archivo.parent.name
    return Skill(nombre, datos.get("description", ""), cuerpo.strip())


def cargar_skills(carpeta: Path) -> dict[str, Skill]:
    skills = {}
    if carpeta.is_dir():
        for archivo in sorted(carpeta.glob("*/SKILL.md")):
            skill = _leer_skill(archivo)
            if skill:
                skills[skill.nombre] = skill
    return skills


def catalogo(skills: dict[str, Skill]) -> str:
    if not skills:
        return ""
    lineas = [f"- {s.nombre}: {s.descripcion}" for s in skills.values()]
    return (
        "Skills disponibles. Antes de una tarea que encaje con alguna, cárgala con "
        "cargar_skill y sigue sus instrucciones:\n" + "\n".join(lineas)
    )


class CargarSkill(Herramienta):
    nombre = "cargar_skill"
    descripcion = "Carga las instrucciones completas de una skill del catálogo."

    def __init__(self, skills: dict[str, Skill]):
        self.skills = skills
        self.parametros = {
            "type": "object",
            "properties": {"nombre": {"type": "string", "enum": list(skills)}},
            "required": ["nombre"],
        }

    def ejecutar(self, nombre: str) -> str:
        skill = self.skills.get(nombre)
        if not skill:
            raise ErrorHerramienta(f"No existe la skill '{nombre}'. Disponibles: {', '.join(self.skills)}")
        return f"Instrucciones de la skill '{nombre}':\n\n{skill.instrucciones}"
