"""FASE 3 — Renderizado desde plantillas: golden files, tags TDAH, idempotencia.

Los golden files (tests/golden/*.md) son el contrato visual de las notas:
convierten "el markdown se ve bien" en un assert de igualdad exacta. Si un
cambio de plantilla es intencional, se regeneran con:

    python tests/regenerar_golden.py
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from datos_compartidos import RESPUESTA_VALIDA
from tdah_estudio.chunker import BloqueEstudio, MicroChunker
from tdah_estudio.config import ConfigTDAH
from tdah_estudio.obsidian import (
    ExportadorObsidian,
    nombre_archivo_bloque,
    render_bloque,
    render_sintesis,
    slug,
)

GOLDEN = Path(__file__).resolve().parent / "golden"
FECHA_FIJA = date(2026, 1, 15)
CFG = ConfigTDAH()


def _bloque(indice: int, total: int, fin_sesion: bool = False) -> BloqueEstudio:
    return BloqueEstudio(
        indice=indice,
        total=total,
        titulo_fuente="Historia Constitucional",
        texto="Texto de prueba del bloque con contenido fijo y determinista.",
        palabras=9,
        minutos_estimados=0.1,
        sesion=1,
        es_fin_de_sesion=fin_sesion,
    )


def _comparar_con_golden(nombre: str, obtenido: str) -> None:
    esperado = (GOLDEN / nombre).read_text(encoding="utf-8")
    assert obtenido == esperado, (
        f"El render de {nombre} cambió. Si el cambio es intencional, "
        f"regenera con: python tests/regenerar_golden.py"
    )


# ======================================================================
# Golden files (DoD FASE 3)
# ======================================================================
def test_golden_bloque_normal() -> None:
    _comparar_con_golden(
        "bloque_normal.md", render_bloque(_bloque(2, 5), CFG, fecha=FECHA_FIJA)
    )


def test_golden_bloque_fin_de_sesion() -> None:
    _comparar_con_golden(
        "bloque_fin_sesion.md",
        render_bloque(_bloque(4, 5, fin_sesion=True), CFG, fecha=FECHA_FIJA),
    )


def test_golden_bloque_ultimo() -> None:
    _comparar_con_golden(
        "bloque_ultimo.md", render_bloque(_bloque(5, 5), CFG, fecha=FECHA_FIJA)
    )


def test_golden_sintesis() -> None:
    _comparar_con_golden(
        "sintesis.md",
        render_sintesis(RESPUESTA_VALIDA, "manual_historia.pdf", fecha=FECHA_FIJA),
    )


def test_golden_dashboard(tmp_path: Path) -> None:
    ExportadorObsidian(CFG).generar(tmp_path)
    obtenido = (tmp_path / "00 - Inicio" / "🏠 Dashboard.md").read_text(encoding="utf-8")
    _comparar_con_golden("dashboard.md", obtenido)


# ======================================================================
# Contenido: variantes, aviso de cobertura, tags TDAH
# ======================================================================
def test_variantes_de_bloque_comparten_plantilla_base() -> None:
    normal = render_bloque(_bloque(2, 5), CFG, fecha=FECHA_FIJA)
    ultimo = render_bloque(_bloque(5, 5), CFG, fecha=FECHA_FIJA)
    # Zona común idéntica (mismo origen), cierre distinto (parámetro).
    assert "## 📖 Lectura" in normal and "## 📖 Lectura" in ultimo
    assert "**Siguiente:**" in normal and "**Siguiente:**" not in ultimo
    assert "Capítulo COMPLETO" in ultimo and "(ÚLTIMO)" in ultimo
    assert "#repaso-48h" in ultimo


def test_aviso_cobertura_aparece_solo_si_existe() -> None:
    con_aviso = dict(RESPUESTA_VALIDA, aviso_cobertura="Quedó fuera el capítulo 3")
    md = render_sintesis(con_aviso, "doc.pdf", fecha=FECHA_FIJA)
    assert "Cobertura parcial" in md and "capítulo 3" in md
    sin_aviso = render_sintesis(RESPUESTA_VALIDA, "doc.pdf", fecha=FECHA_FIJA)
    assert "Cobertura parcial" not in sin_aviso


def test_vault_contiene_los_tags_tdah_del_contrato(tmp_path: Path) -> None:
    ExportadorObsidian(CFG).generar(tmp_path)
    todo = "\n".join(
        p.read_text(encoding="utf-8") for p in tmp_path.rglob("*.md")
    )
    for tag in ("#baja-energia", "#alta-energia", "#bloque-20min",
                "#recompensa-dopamina", "#repaso-48h"):
        assert tag in todo, f"el vault perdió el tag {tag}"
    assert "```dataview" in todo


def test_vault_refleja_la_configuracion(tmp_path: Path) -> None:
    cfg = ConfigTDAH(minutos_por_bloque=20, bloques_por_sesion_max=3,
                     minutos_lectura_efectiva=11)
    ExportadorObsidian(cfg).generar(tmp_path)
    reglas = (tmp_path / "00 - Inicio" / "📜 Reglas del sistema.md").read_text(
        encoding="utf-8"
    )
    assert "Un bloque = 20 minutos" in reglas
    assert "Máximo 3 bloques" in reglas
    sesion = (tmp_path / "99 - Plantillas" / "Plantilla - Sesión diaria.md").read_text(
        encoding="utf-8"
    )
    assert "Bloque 3: [[ ]]" in sesion and "Bloque 4" not in sesion


# ======================================================================
# Idempotencia (DoD FASE 3): invariante declarado en FASE 0
# ======================================================================
def test_vault_idempotente_no_pisa_notas_de_usuario(tmp_path: Path) -> None:
    exportador = ExportadorObsidian(CFG)
    exportador.generar(tmp_path)
    nota = tmp_path / "02 - Derecho" / "mi_apunte_irremplazable.md"
    nota.write_text("apunte irremplazable", encoding="utf-8")
    dashboard = tmp_path / "00 - Inicio" / "🏠 Dashboard.md"
    dashboard.write_text("dashboard corrompido por accidente", encoding="utf-8")

    exportador.generar(tmp_path)

    # La nota del usuario sobrevive intacta; el archivo de sistema se repone.
    assert nota.read_text(encoding="utf-8") == "apunte irremplazable"
    assert "Regla de oro" in dashboard.read_text(encoding="utf-8")


# ======================================================================
# Nombres de archivo y enlaces entre bloques
# ======================================================================
def test_enlace_siguiente_coincide_con_nombre_de_archivo() -> None:
    """El [[enlace]] del bloque N debe apuntar EXACTAMENTE al archivo N+1:
    un enlace roto en Obsidian es un callejón sin salida a mitad de sesión."""
    texto = "\n\n".join(
        " ".join(f"palabra{k}x{i}" for i in range(18)) for k in range(3)
    )
    cfg = ConfigTDAH(ppm_lectura_densa=10, minutos_lectura_efectiva=2)
    bloques = MicroChunker(cfg).dividir(texto, "Título: ¿con símbolos raros?")
    md_primero = render_bloque(bloques[0], cfg, fecha=FECHA_FIJA)
    nombre_segundo = nombre_archivo_bloque(bloques[1])
    assert f"[[{nombre_segundo.removesuffix('.md')}]]" in md_primero


def test_slug_elimina_simbolos_conservando_acentos() -> None:
    assert slug("Título: ¿raro? / peligroso\\") == "Título raro peligroso"
    assert slug("  espacios   múltiples  ") == "espacios múltiples"
