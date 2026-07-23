"""FASE 1a — Contrato de carga de configuración: degradar sí, en silencio no."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tdah_estudio.config import ConfigTDAH, cargar_config


def _escribir(tmp_path: Path, datos: object) -> Path:
    ruta = tmp_path / "config_tdah.json"
    ruta.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    return ruta


def test_defaults_sin_archivo() -> None:
    cfg = cargar_config(None)
    assert cfg.minutos_por_bloque == 15
    assert cfg.palabras_por_bloque == 110 * 11


def test_archivo_inexistente_usa_defaults_sin_aviso(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = cargar_config(tmp_path / "no_existe.json")
    assert cfg == ConfigTDAH()
    assert capsys.readouterr().err == ""


def test_archivo_valido_se_aplica(tmp_path: Path) -> None:
    ruta = _escribir(tmp_path, {"minutos_por_bloque": 20, "modelo_llm": "claude-opus-4-8"})
    cfg = cargar_config(ruta)
    assert cfg.minutos_por_bloque == 20
    assert cfg.modelo_llm == "claude-opus-4-8"


def test_clave_comentario_dolar_se_ignora_en_silencio(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ruta = _escribir(tmp_path, {"$comentario": "bla", "ppm_lectura_densa": 120})
    cfg = cargar_config(ruta)
    assert cfg.ppm_lectura_densa == 120
    assert capsys.readouterr().err == ""


def test_clave_desconocida_avisa_por_stderr_y_se_descarta(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # El caso exacto que motivó la regla: typo en el nombre del campo.
    ruta = _escribir(tmp_path, {"minutos_por_bloqe": 20})
    cfg = cargar_config(ruta)
    err = capsys.readouterr().err
    assert "minutos_por_bloqe" in err and "desconocida" in err
    assert cfg.minutos_por_bloque == 15  # el typo NO configuró nada


def test_valor_fuera_de_rango_avisa_y_usa_defecto(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ruta = _escribir(tmp_path, {"ppm_lectura_densa": 1100})
    cfg = cargar_config(ruta)
    err = capsys.readouterr().err
    assert "fuera de rango" in err and "1100" in err
    assert cfg.ppm_lectura_densa == 110


def test_tipo_incorrecto_avisa_y_usa_defecto(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ruta = _escribir(tmp_path, {"minutos_por_bloque": "quince", "modelo_llm": "  "})
    cfg = cargar_config(ruta)
    err = capsys.readouterr().err
    assert "entero" in err and "modelo_llm" in err
    assert cfg.minutos_por_bloque == 15
    assert cfg.modelo_llm == "claude-sonnet-5"


def test_json_ilegible_avisa_y_usa_todos_los_defaults(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ruta = tmp_path / "roto.json"
    ruta.write_text("{esto no es json", encoding="utf-8")
    cfg = cargar_config(ruta)
    assert "no se pudo leer" in capsys.readouterr().err
    assert cfg == ConfigTDAH()


def test_json_no_objeto_avisa(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    ruta = _escribir(tmp_path, [1, 2, 3])
    cfg = cargar_config(ruta)
    assert "no contiene un objeto" in capsys.readouterr().err
    assert cfg == ConfigTDAH()


def test_coherencia_cruzada_ajusta_lectura_que_no_cabe(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # 14 de lectura + 2 recuperación + 2 pausa = 18 > bloque de 15: imposible.
    ruta = _escribir(tmp_path, {"minutos_lectura_efectiva": 14})
    cfg = cargar_config(ruta)
    err = capsys.readouterr().err
    assert "no cabe" in err
    assert cfg.minutos_lectura_efectiva == 15 - (2 + cfg.minutos_pausa_corta)


def test_config_del_repositorio_carga_sin_avisos(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """El config_tdah.json commiteado debe ser siempre 100% válido."""
    ruta = Path(__file__).resolve().parent.parent / "config_tdah.json"
    cfg = cargar_config(ruta)
    assert capsys.readouterr().err == ""
    assert cfg == ConfigTDAH()
