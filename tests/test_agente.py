"""Pruebas sin micrófono, sin voz y sin modelo real.

Ejecutar desde la raíz del proyecto:  python -m pytest -q
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agente import Agente  # noqa: E402
from herramientas.archivos import (  # noqa: E402
    AgregarAlArchivo, BuscarArchivos, CrearArchivo, EditarArchivo, LeerArchivo, ListarCarpeta,
)
from herramientas.base import ErrorHerramienta  # noqa: E402
from herramientas.espacio import Espacio  # noqa: E402
from herramientas.skills import CargarSkill, cargar_skills, catalogo  # noqa: E402
from llm.base import LLM, LlamadaHerramienta, RespuestaLLM  # noqa: E402
from llm.claude_llm import ClaudeLLM  # noqa: E402
from llm.ollama_llm import OllamaLLM  # noqa: E402
from utils.respuestas import es_afirmativa  # noqa: E402

RAIZ_PROYECTO = Path(__file__).resolve().parents[1]


@pytest.fixture
def casa(tmp_path):
    """Una carpeta personal falsa con algunos archivos."""
    (tmp_path / "Documentos" / "Universidad").mkdir(parents=True)
    (tmp_path / "Descargas").mkdir()
    (tmp_path / ".ssh").mkdir()
    (tmp_path / ".ssh" / "id_ed25519").write_text("SECRETO")
    (tmp_path / "Documentos" / "Universidad" / "Informe_Investigacion_Operaciones.txt").write_text(
        "Método húngaro aplicado a la asignación de turnos.", encoding="utf-8"
    )
    (tmp_path / "Descargas" / "notas.md").write_text("# Notas\nPrimera idea", encoding="utf-8")
    return tmp_path


@pytest.fixture
def espacio(casa):
    return Espacio(casa, {"node_modules"})


# ---------- seguridad ----------
def test_rutas_fuera_o_ocultas_se_rechazan(espacio):
    for ruta in ["/etc/passwd", "../../etc", ".ssh/id_ed25519", "Documentos/../.ssh"]:
        with pytest.raises(ErrorHerramienta):
            espacio.resolver(ruta)


def test_rutas_aproximadas_por_voz(espacio, casa):
    assert espacio.resolver("documentos/universidad") == casa / "Documentos" / "Universidad"
    assert espacio.resolver("Documents") == casa / "Documentos"  # sinónimo inglés
    assert espacio.resolver(f"{casa}/Descargas/notas.md") == casa / "Descargas" / "notas.md"


def test_enlace_simbolico_hacia_fuera(espacio, casa, tmp_path_factory):
    fuera = tmp_path_factory.mktemp("fuera")
    (fuera / "secreto.txt").write_text("x")
    (casa / "atajo").symlink_to(fuera)
    with pytest.raises(ErrorHerramienta):
        espacio.resolver("atajo/secreto.txt")


# ---------- herramientas ----------
def test_buscar_encuentra_y_no_mira_ocultos(espacio):
    buscar = BuscarArchivos(espacio)
    r = buscar.ejecutar(consulta="informe operaciones")
    assert "Informe_Investigacion_Operaciones.txt" in r
    assert "id_ed25519" not in buscar.ejecutar(consulta="id ed25519")


def test_listar(espacio):
    r = ListarCarpeta(espacio).ejecutar(carpeta="")
    assert "Documentos/" in r and ".ssh" not in r


def test_crear_leer_editar_docx(espacio, casa, tmp_path_factory):
    respaldos = tmp_path_factory.mktemp("respaldos")
    crear = CrearArchivo(espacio)
    assert "Creado" in crear.ejecutar(
        ruta="Documentos/resumen", contenido="# Resumen\n- Punto uno\nTexto del párrafo."
    )
    assert (casa / "Documentos" / "resumen.docx").exists()
    with pytest.raises(ErrorHerramienta):  # no sobrescribe
        crear.ejecutar(ruta="Documentos/resumen.docx", contenido="otra cosa")

    leer = LeerArchivo(espacio, tam_parte=3000)
    assert "Punto uno" in leer.ejecutar(ruta="documentos/resumen.docx")

    editar = EditarArchivo(espacio, respaldos)
    assert "1 reemplazo" in editar.ejecutar(
        ruta="Documentos/resumen.docx", buscar="Punto uno", reemplazar="Punto corregido"
    )
    assert "Punto corregido" in leer.ejecutar(ruta="Documentos/resumen.docx")
    assert len(list(respaldos.iterdir())) == 1  # se guardó el original

    AgregarAlArchivo(espacio, respaldos).ejecutar(ruta="Documentos/resumen.docx", contenido="Final")
    assert "Final" in leer.ejecutar(ruta="Documentos/resumen.docx")


def test_leer_por_partes(espacio, casa):
    (casa / "Descargas" / "largo.txt").write_text("a" * 7000)
    leer = LeerArchivo(espacio, tam_parte=3000)
    assert "Parte 1 de 3" in leer.ejecutar(ruta="Descargas/largo.txt")
    assert "Parte 3 de 3" in leer.ejecutar(ruta="Descargas/largo.txt", parte=3)


def test_editar_texto_inexistente(espacio, tmp_path_factory):
    editar = EditarArchivo(espacio, tmp_path_factory.mktemp("r"))
    with pytest.raises(ErrorHerramienta):
        editar.ejecutar(ruta="Descargas/notas.md", buscar="no existe", reemplazar="x")


def test_skills_del_proyecto():
    skills = cargar_skills(RAIZ_PROYECTO / "skills")
    assert {"documentos", "busqueda-archivos"} <= set(skills)
    assert "documentos" in catalogo(skills)
    assert "leer_archivo" in CargarSkill(skills).ejecutar(nombre="documentos")


# ---------- respuestas sí/no ----------
@pytest.mark.parametrize("texto,esperado", [
    ("Sí, hazlo", True), ("dale", True), ("yes please", True),
    ("no", False), ("mejor no", False), ("eh... no sé", False), (None, False), ("", False),
])
def test_es_afirmativa(texto, esperado):
    assert es_afirmativa(texto) is esperado


# ---------- bucle del agente con un modelo simulado ----------
class ModeloGuionado(LLM):
    """Devuelve respuestas predefinidas, una por llamada."""
    def __init__(self, guion):
        self.guion = list(guion)
        self.vistos = []

    def responder(self, sistema, mensajes, herramientas=None):
        self.vistos.append(list(mensajes))
        return self.guion.pop(0)


def _agente(modelo, herramientas, confirmar=lambda p: True):
    avisos = []
    agente = Agente(modelo, herramientas, "sistema", max_pasos=4, max_historial=20,
                    max_resultado=3500, avisar=avisos.append, confirmar=confirmar)
    return agente, avisos


def test_agente_busca_y_responde(espacio):
    modelo = ModeloGuionado([
        RespuestaLLM("", [LlamadaHerramienta("1", "buscar_archivos", {"consulta": "notas", "inventado": 1})]),
        RespuestaLLM("Encontré tus notas en Descargas."),
    ])
    agente, avisos = _agente(modelo, {"buscar_archivos": BuscarArchivos(espacio)})
    assert agente.procesar("busca mis notas", "es") == "Encontré tus notas en Descargas."
    assert avisos == ["Buscando notas."]
    resultado = modelo.vistos[1][-1]
    assert resultado["role"] == "herramienta" and "notas.md" in resultado["content"]
    # el historial solo conserva la conversación, no los pasos intermedios
    assert [m["role"] for m in agente.historial] == ["user", "assistant"]
    assert "Responde únicamente en español" in modelo.vistos[0][-1]["content"]


def test_agente_respeta_cancelacion(espacio, casa, tmp_path_factory):
    modelo = ModeloGuionado([
        RespuestaLLM("", [LlamadaHerramienta("1", "editar_archivo", {
            "ruta": "Descargas/notas.md", "buscar": "Primera", "reemplazar": "Segunda"})]),
        RespuestaLLM("Vale, no lo cambio."),
    ])
    preguntas = []
    agente, _ = _agente(
        modelo, {"editar_archivo": EditarArchivo(espacio, tmp_path_factory.mktemp("r"))},
        confirmar=lambda p: preguntas.append(p) or False,
    )
    agente.procesar("cambia primera por segunda en notas", "es")
    assert preguntas == ["¿Cambio «Primera» por «Segunda» en notas?"]
    assert "Primera idea" in (casa / "Descargas" / "notas.md").read_text(encoding="utf-8")


def test_agente_limite_de_pasos(espacio):
    bucle = RespuestaLLM("", [LlamadaHerramienta("1", "listar_carpeta", {})])
    agente, _ = _agente(ModeloGuionado([bucle] * 4), {"listar_carpeta": ListarCarpeta(espacio)})
    assert "No alcancé" in agente.procesar("algo", "es")


# ---------- traducción de historial a cada proveedor ----------
HISTORIAL = [
    {"role": "user", "content": "lee notas"},
    {"role": "assistant", "content": "", "llamadas": [LlamadaHerramienta("ab", "leer_archivo", {"ruta": "x"})]},
    {"role": "herramienta", "id": "ab", "nombre": "leer_archivo", "content": "texto"},
]


def test_traduccion_ollama():
    t = OllamaLLM._traducir(HISTORIAL)
    assert t[1]["tool_calls"][0]["function"]["name"] == "leer_archivo"
    assert t[2] == {"role": "tool", "tool_name": "leer_archivo", "content": "texto"}


def test_traduccion_claude():
    t = ClaudeLLM._traducir(HISTORIAL)
    assert t[1]["content"][0] == {"type": "tool_use", "id": "ab", "name": "leer_archivo", "input": {"ruta": "x"}}
    assert t[2] == {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "ab", "content": "texto"}]}
