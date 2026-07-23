"""FASE 0 — Invariantes del sistema declarados ANTES de la implementación.

Cada test está marcado xfail con la fase que debe encenderlo. Cuando una fase
aterriza, su test se reescribe en el archivo definitivo (test_chunker.py,
test_prompts.py, test_obsidian.py) y aquí se elimina. Este archivo debe quedar
VACÍO de tests al cierre de la FASE 4: es el burn-down chart del proyecto.

Los imports van DENTRO de cada test a propósito: los módulos aún no existen
y un ImportError a nivel de módulo rompería la colección de pytest en vez de
registrarse como xfail.
"""

from __future__ import annotations

import pytest


@pytest.mark.xfail(reason="FASE 1a pendiente: config con avisos", strict=False)
def test_config_avisa_claves_desconocidas() -> None:
    from tdah_estudio.config import ConfigTDAH  # noqa: F401

    raise AssertionError("se implementa en tests/test_config.py")


@pytest.mark.xfail(reason="FASE 1b pendiente: chunker puro", strict=False)
def test_chunker_no_pierde_palabras() -> None:
    from tdah_estudio.chunker import MicroChunker  # noqa: F401

    raise AssertionError("se implementa en tests/test_chunker.py (hypothesis)")


@pytest.mark.xfail(reason="FASE 1b pendiente: chunker puro", strict=False)
def test_chunker_respeta_presupuesto_120pct() -> None:
    from tdah_estudio.chunker import MicroChunker  # noqa: F401

    raise AssertionError("se implementa en tests/test_chunker.py (hypothesis)")


@pytest.mark.xfail(reason="FASE 2 pendiente: contrato LLM", strict=False)
def test_contrato_llm_rechaza_respuestas_invalidas() -> None:
    from tdah_estudio.prompts import GeneradorPrompt  # noqa: F401

    raise AssertionError("se implementa en tests/test_prompts.py")


@pytest.mark.xfail(reason="FASE 3 pendiente: renderizado desde plantillas", strict=False)
def test_vault_idempotente_no_pisa_notas_de_usuario() -> None:
    from tdah_estudio.obsidian import ExportadorObsidian  # noqa: F401

    raise AssertionError("se implementa en tests/test_obsidian.py")


@pytest.mark.xfail(reason="FASE 4 pendiente: round-trip PDF→markdown", strict=False)
def test_round_trip_pdf_a_markdown() -> None:
    from tdah_estudio.cli import main  # noqa: F401

    raise AssertionError("se implementa en tests/test_cli_roundtrip.py")
