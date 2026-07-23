"""FASE 4 — Round-trip completo y contrato de la CLI.

El round-trip cubre la cadena entera que en la iteración 1 solo se probó
por eslabones: PDF real → chunk → payload → respuesta LLM simulada →
validación → markdown final. También se ejercitan TODOS los caminos de
error de documentos.py (restricción 7: cero código sin ejecutar).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import tdah_estudio.documentos as documentos
from datos_compartidos import RESPUESTA_VALIDA
from tdah_estudio.chunker import MicroChunker
from tdah_estudio.cli import main
from tdah_estudio.config import ConfigTDAH
from tdah_estudio.documentos import ErrorDocumento, leer_documento
from tdah_estudio.obsidian import render_sintesis
from tdah_estudio.prompts import payload_api, validar_respuesta

FIXTURES = Path(__file__).resolve().parent / "fixtures"
PDF_REAL = FIXTURES / "documento_2pag.pdf"
PDF_ESCANEADO = FIXTURES / "documento_escaneado.pdf"


# ======================================================================
# Round-trip (DoD FASE 4)
# ======================================================================
def test_round_trip_pdf_a_markdown_final() -> None:
    # 1. PDF real de 2 páginas -> texto
    texto = leer_documento(PDF_REAL)
    assert "nulidad de derecho publico" in texto

    # 2. texto -> bloques de estudio (presupuesto pequeño para forzar >1 bloque)
    cfg = ConfigTDAH(ppm_lectura_densa=40, minutos_lectura_efectiva=1, modelo_llm="modelo-test")
    bloques = MicroChunker(cfg).dividir(texto, "Nulidad de Derecho Público")
    assert len(bloques) >= 2
    assert sum(b.palabras for b in bloques) == len(texto.split())

    # 3. texto -> payload para la API (modelo desde config)
    payload = payload_api(cfg, texto, materia="Derecho")
    assert payload["model"] == "modelo-test"
    json.dumps(payload)

    # 4. respuesta simulada del LLM -> validación -> nota de síntesis
    respuesta_llm = json.dumps(RESPUESTA_VALIDA, ensure_ascii=False)
    datos = validar_respuesta(respuesta_llm)
    nota = render_sintesis(datos, PDF_REAL.name)
    assert "## 🎯 Active Recall" in nota
    assert "## 🪄 Analogía Feynman" in nota
    assert "#repaso-48h" in nota


# ======================================================================
# CLI: subcomandos felices
# ======================================================================
def test_cli_chunk_txt_escribe_notas_enlazadas(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fuente = tmp_path / "capitulo_uno.txt"
    fuente.write_text(documentos.TEXTO_DEMO * 8, encoding="utf-8")
    salida = tmp_path / "bloques"

    codigo = main(["--config", str(tmp_path / "sin_config.json"),
                   "chunk", str(fuente), "--salida", str(salida)])

    assert codigo == 0
    notas = sorted(salida.glob("*.md"))
    assert len(notas) >= 2
    stdout = capsys.readouterr().out
    assert "PLAN DE ESTUDIO" in stdout and "Siguiente acción" in stdout
    # El título por defecto se deriva del nombre del archivo.
    assert "Capitulo Uno" in notas[0].name
    # El enlace del bloque 1 apunta al archivo del bloque 2 (sin extensión).
    contenido_1 = next(p for p in notas if "Bloque 1 de" in p.name).read_text(encoding="utf-8")
    nombre_2 = next(p for p in notas if "Bloque 2 de" in p.name).name
    assert f"[[{nombre_2[:-3]}]]" in contenido_1


def test_cli_chunk_pdf_real(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    salida = tmp_path / "bloques_pdf"
    codigo = main(["chunk", str(PDF_REAL), "--titulo", "Fixture Legal",
                   "--salida", str(salida)])
    assert codigo == 0
    assert any("Fixture Legal" in p.name for p in salida.glob("*.md"))


def test_cli_prompt_imprime_contrato(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["prompt", "--materia", "Historia"]) == 0
    out = capsys.readouterr().out
    assert "Procesador de Estudio TDAH" in out and "Historia" in out


def test_cli_prompt_payload_es_json_valido(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    doc = tmp_path / "doc.txt"
    doc.write_text("Texto breve del documento legal.", encoding="utf-8")
    assert main(["prompt", "--payload", str(doc)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["model"] == ConfigTDAH().modelo_llm
    assert "Texto breve del documento legal." in payload["messages"][0]["content"]


def test_cli_vault_y_demo(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["vault", "--salida", str(tmp_path / "v")]) == 0
    assert (tmp_path / "v" / "00 - Inicio" / "🏠 Dashboard.md").exists()
    assert main(["demo", "--salida", str(tmp_path / "v2")]) == 0
    out = capsys.readouterr().out
    assert "DEMO 3/3" in out


def test_cli_respeta_config_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = tmp_path / "config_tdah.json"
    config.write_text(json.dumps({"modelo_llm": "modelo-de-config"}), encoding="utf-8")
    doc = tmp_path / "doc.txt"
    doc.write_text("Contenido del documento.", encoding="utf-8")
    assert main(["--config", str(config), "prompt", "--payload", str(doc)]) == 0
    assert json.loads(capsys.readouterr().out)["model"] == "modelo-de-config"


# ======================================================================
# Caminos de error (restricción 7: todos ejercitados)
# ======================================================================
def test_cli_archivo_inexistente_sale_2_con_mensaje(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["chunk", "no_existe.txt"]) == 2
    assert "No existe el archivo" in capsys.readouterr().err


def test_cli_pdf_escaneado_sale_2_con_mensaje_ocr(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["chunk", str(PDF_ESCANEADO), "--salida", str(tmp_path)]) == 2
    err = capsys.readouterr().err
    assert "OCR" in err and "escaneado" in err


def test_sin_pypdf_error_con_instrucciones(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(documentos, "_PDF_DISPONIBLE", False)
    with pytest.raises(ErrorDocumento, match="pip install"):
        leer_documento(PDF_REAL)


def test_texto_sin_parrafos_sale_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    vacio = tmp_path / "vacio.txt"
    vacio.write_text("   \n\n  ", encoding="utf-8")
    assert main(["chunk", str(vacio)]) == 2
    assert "PDF escaneado" in capsys.readouterr().err
