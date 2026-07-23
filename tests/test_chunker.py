"""FASE 1b — Chunker: casos dirigidos + invariantes verificados con hypothesis.

Los tests usan un presupuesto artificialmente pequeño (20 palabras por bloque:
ppm=10 x 2 min) para que los casos borde sean legibles a simple vista. Los
rangos del JSON no aplican aquí: la construcción directa del dataclass es la
vía de test documentada.
"""

from __future__ import annotations

import math

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from tdah_estudio.chunker import MicroChunker
from tdah_estudio.config import ConfigTDAH

# Presupuesto de test: 10 ppm x 2 min = 20 palabras por bloque.
CFG = ConfigTDAH(ppm_lectura_densa=10, minutos_lectura_efectiva=2)
PRESUPUESTO = CFG.palabras_por_bloque


def _parrafo(n_palabras: int, semilla: str = "palabra") -> str:
    return " ".join(f"{semilla}{i}" for i in range(n_palabras))


# ======================================================================
# Casos dirigidos (DoD FASE 1)
# ======================================================================
def test_presupuesto_de_palabras_se_respeta() -> None:
    texto = "\n\n".join(_parrafo(12, f"p{k}x") for k in range(10))  # 120 palabras
    bloques = MicroChunker(CFG).dividir(texto, "Presupuesto")
    assert len(bloques) > 1
    assert all(b.palabras <= PRESUPUESTO * 1.2 for b in bloques)
    assert sum(b.palabras for b in bloques) == 120


def test_parrafo_gigante_se_subdivide_por_oraciones() -> None:
    oracion = "Aaa bbb ccc ddd eee."  # 5 palabras, cierra oración de verdad
    gigante = " ".join(oracion for _ in range(12))  # 60 palabras, 3x presupuesto
    bloques = MicroChunker(CFG).dividir(gigante, "Gigante")
    assert len(bloques) >= 3
    assert all(b.palabras <= PRESUPUESTO * 1.2 for b in bloques)
    assert sum(b.palabras for b in bloques) == 60


def test_bloque_enano_final_se_fusiona() -> None:
    # Paquetes naturales: [18], [18], [3]. El de 3 (<40% de 20) debe
    # fusionarse con el anterior porque 21 <= 24 (120%).
    texto = "\n\n".join([_parrafo(18, "a"), _parrafo(18, "b"), _parrafo(3, "c")])
    bloques = MicroChunker(CFG).dividir(texto, "Enano")
    assert [b.palabras for b in bloques] == [18, 21]


def test_bloque_enano_no_se_fusiona_si_desborda() -> None:
    # [20], [20], [7]: 7 < 8 (40%) pero 27 > 24 (120%): debe quedar aparte.
    texto = "\n\n".join([_parrafo(20, "a"), _parrafo(20, "b"), _parrafo(7, "c")])
    bloques = MicroChunker(CFG).dividir(texto, "NoFusion")
    assert [b.palabras for b in bloques] == [20, 20, 7]


def test_abreviaturas_juridicas_no_cortan_oracion() -> None:
    frase = (
        "El art. 19 inc. 2 consagra garantías según cfr. Bidart y "
        "la doctrina de op. cit. La regla viene de las Cortes del S. XIX "
        "y de los arts. 5 y ss. En la práctica rige siempre."
    )
    gigante = " ".join(frase for _ in range(4))  # fuerza subdivisión
    bloques = MicroChunker(CFG).dividir(gigante, "Abreviaturas")
    finales_prohibidos = ("art.", "arts.", "inc.", "cfr.", "cit.", "ss.", "S.")
    for b in bloques:
        assert not b.texto.rstrip().endswith(finales_prohibidos), (
            f"bloque cortado tras abreviatura: ...{b.texto[-40:]!r}"
        )
    total_original = len(gigante.split())
    assert sum(b.palabras for b in bloques) == total_original


@pytest.mark.parametrize("texto", ["", "   \n\n  ", "una dos\n\nuno"])
def test_texto_vacio_o_solo_ruido_falla_con_mensaje_accionable(texto: str) -> None:
    with pytest.raises(ValueError, match="PDF escaneado"):
        MicroChunker(CFG).dividir(texto, "Vacío")


def test_sesiones_y_descansos() -> None:
    texto = "\n\n".join(_parrafo(18, f"s{k}x") for k in range(8))  # 8 bloques
    bloques = MicroChunker(CFG).dividir(texto, "Sesiones")
    assert len(bloques) == 8
    assert [b.sesion for b in bloques] == [1, 1, 1, 1, 2, 2, 2, 2]
    # Descanso largo tras el bloque 4; el bloque 8 es el último: sin descanso.
    assert [b.es_fin_de_sesion for b in bloques] == [
        False, False, False, True, False, False, False, False,
    ]


def test_resumen_plan_contiene_el_contrato_completo() -> None:
    texto = "\n\n".join(_parrafo(18, f"r{k}x") for k in range(5))
    chunker = MicroChunker(CFG)
    bloques = chunker.dividir(texto, "Historia Constitucional")
    plan = chunker.resumen_plan(bloques)
    assert "Historia Constitucional" in plan
    assert f"Bloques de {CFG.minutos_por_bloque} min : {len(bloques)}" in plan
    assert "descanso largo" in plan


# ======================================================================
# Invariantes con hypothesis (DoD FASE 1)
# ======================================================================
_PALABRA = st.text(alphabet="abcdefghij", min_size=1, max_size=7)


@st.composite
def _oracion(draw: st.DrawFn) -> str:
    """Oración de 3-8 palabras, primera capitalizada, cierre con punto.

    El límite de 8 palabras garantiza la precondición del invariante I2:
    ninguna oración individual excede el presupuesto de 20.
    """
    palabras = draw(st.lists(_PALABRA, min_size=3, max_size=8))
    palabras[0] = palabras[0].capitalize()
    return " ".join(palabras) + "."


@st.composite
def _texto_documento(draw: st.DrawFn) -> str:
    parrafos = draw(
        st.lists(
            st.lists(_oracion(), min_size=1, max_size=6).map(" ".join),
            min_size=1,
            max_size=8,
        )
    )
    return "\n\n".join(parrafos)


@settings(max_examples=200, deadline=None)
@given(_texto_documento())
def test_invariante_I1_ninguna_palabra_se_pierde(texto: str) -> None:
    esperadas = len(texto.split())
    bloques = MicroChunker(CFG).dividir(texto, "I1")
    assert sum(b.palabras for b in bloques) == esperadas


@settings(max_examples=200, deadline=None)
@given(_texto_documento())
def test_invariante_I2_ningun_bloque_excede_120pct(texto: str) -> None:
    bloques = MicroChunker(CFG).dividir(texto, "I2")
    tope = PRESUPUESTO * 1.2
    assert all(b.palabras <= tope for b in bloques), [b.palabras for b in bloques]


@settings(max_examples=200, deadline=None)
@given(_texto_documento())
def test_invariantes_I3_I4_indices_y_sesiones(texto: str) -> None:
    bloques = MicroChunker(CFG).dividir(texto, "I3I4")
    total = len(bloques)
    assert [b.indice for b in bloques] == list(range(1, total + 1))
    assert all(b.total == total for b in bloques)
    for b in bloques:
        assert b.sesion == math.ceil(b.indice / CFG.bloques_por_sesion_max)
        es_multiplo = b.indice % CFG.bloques_por_sesion_max == 0
        assert b.es_fin_de_sesion == (es_multiplo and b.indice < total)
