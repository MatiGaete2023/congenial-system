"""Regenera los golden files de tests/golden/ tras un cambio INTENCIONAL
de plantillas. Uso:

    python tests/regenerar_golden.py

Después: revisar el diff con `git diff tests/golden/` ANTES de commitear.
El golden file es un contrato visual; regenerarlo sin mirar el diff es
firmarlo sin leerlo.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

_AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(_AQUI.parent / "src"))
sys.path.insert(0, str(_AQUI))

from datos_compartidos import RESPUESTA_VALIDA  # noqa: E402
from tdah_estudio.chunker import BloqueEstudio  # noqa: E402
from tdah_estudio.config import ConfigTDAH  # noqa: E402
from tdah_estudio.obsidian import (  # noqa: E402
    ExportadorObsidian,
    render_bloque,
    render_sintesis,
)

GOLDEN = _AQUI / "golden"
FECHA_FIJA = date(2026, 1, 15)
CFG = ConfigTDAH()


def _bloque(indice: int, total: int, fin_sesion: bool = False) -> BloqueEstudio:
    """Debe ser IDÉNTICO al helper de test_obsidian.py: mismo insumo, mismo golden."""
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


def main() -> None:
    GOLDEN.mkdir(exist_ok=True)
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        ExportadorObsidian(CFG).generar(Path(tmp))
        dashboard = (Path(tmp) / "00 - Inicio" / "🏠 Dashboard.md").read_text(
            encoding="utf-8"
        )

    contenidos = {
        "bloque_normal.md": render_bloque(_bloque(2, 5), CFG, fecha=FECHA_FIJA),
        "bloque_fin_sesion.md": render_bloque(
            _bloque(4, 5, fin_sesion=True), CFG, fecha=FECHA_FIJA
        ),
        "bloque_ultimo.md": render_bloque(_bloque(5, 5), CFG, fecha=FECHA_FIJA),
        "sintesis.md": render_sintesis(
            RESPUESTA_VALIDA, "manual_historia.pdf", fecha=FECHA_FIJA
        ),
        "dashboard.md": dashboard,
    }
    for nombre, contenido in contenidos.items():
        (GOLDEN / nombre).write_text(contenido, encoding="utf-8")
        print(f"  ✓ tests/golden/{nombre}")
    print("Revisa el diff antes de commitear: git diff tests/golden/")


if __name__ == "__main__":
    main()
