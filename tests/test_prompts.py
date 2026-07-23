"""FASE 2 — Contrato LLM: respuesta válida pasa; 6 variantes inválidas fallan
con mensaje accionable; payload serializable con modelo leído del config."""

from __future__ import annotations

import copy
import json
from typing import Any

import pytest

from datos_compartidos import RESPUESTA_VALIDA
from tdah_estudio.config import ConfigTDAH
from tdah_estudio.prompts import payload_api, system_prompt, validar_respuesta


# ======================================================================
# System prompt y payload
# ======================================================================
def test_system_prompt_contiene_el_contrato_completo() -> None:
    prompt = system_prompt(materia="Historia", idioma="español")
    for obligatorio in (
        "resumen_ejecutivo",
        "active_recall",
        "analogia_feynman",
        "donde_se_rompe",
        "Máximo 25 palabras",
        "JSON estricto",
        "Historia",
    ):
        assert obligatorio in prompt, f"el prompt perdió la cláusula: {obligatorio}"


def test_payload_usa_modelo_del_config_y_es_serializable() -> None:
    cfg = ConfigTDAH(modelo_llm="claude-opus-4-8")
    payload = payload_api(cfg, "texto del documento", materia="Derecho")
    assert payload["model"] == "claude-opus-4-8"
    assert "texto del documento" in payload["messages"][0]["content"]
    assert "Derecho" in payload["system"]
    json.dumps(payload)  # debe ser serializable sin TypeError


# ======================================================================
# Validación: la respuesta válida pasa
# ======================================================================
def test_respuesta_valida_pasa() -> None:
    datos = validar_respuesta(json.dumps(RESPUESTA_VALIDA, ensure_ascii=False))
    assert datos["titulo_unidad"].startswith("Régimen")


# ======================================================================
# Validación: 6 variantes inválidas fallan con mensaje accionable (DoD FASE 2)
# ======================================================================
def _variante(mutador: Any) -> str:
    copia = copy.deepcopy(RESPUESTA_VALIDA)
    mutador(copia)
    return json.dumps(copia, ensure_ascii=False)


def test_invalida_1_no_es_json() -> None:
    with pytest.raises(ValueError, match="no devolvió JSON válido"):
        validar_respuesta("El resumen es el siguiente: ...")


def test_invalida_2_resumen_con_2_vinetas() -> None:
    crudo = _variante(lambda d: d["resumen_ejecutivo"].pop())
    with pytest.raises(ValueError, match="exactamente 3 viñetas"):
        validar_respuesta(crudo)


def test_invalida_3_vineta_desbordada() -> None:
    crudo = _variante(
        lambda d: d["resumen_ejecutivo"].__setitem__(0, "palabra " * 31)
    )
    with pytest.raises(ValueError, match="viñeta 1 excede 30 palabras"):
        validar_respuesta(crudo)


def test_invalida_4_recall_con_2_preguntas() -> None:
    crudo = _variante(lambda d: d["active_recall"].pop())
    with pytest.raises(ValueError, match="exactamente 3 preguntas"):
        validar_respuesta(crudo)


def test_invalida_5_pregunta_sin_pista() -> None:
    crudo = _variante(lambda d: d["active_recall"][1].pop("pista"))
    with pytest.raises(ValueError, match="pregunta 2: falta campo 'pista'"):
        validar_respuesta(crudo)


def test_invalida_6_analogia_sin_donde_se_rompe() -> None:
    crudo = _variante(lambda d: d["analogia_feynman"].__setitem__("donde_se_rompe", "  "))
    with pytest.raises(ValueError, match="analogia_feynman: falta campo 'donde_se_rompe'"):
        validar_respuesta(crudo)


def test_errores_se_acumulan_en_un_solo_mensaje() -> None:
    """Un reintento debe poder corregir TODO de una vez, no error por error."""
    crudo = _variante(
        lambda d: (d.pop("titulo_unidad"), d.pop("analogia_feynman"))
    )
    with pytest.raises(ValueError) as exc:
        validar_respuesta(crudo)
    mensaje = str(exc.value)
    assert "titulo_unidad" in mensaje and "analogia_feynman" in mensaje
