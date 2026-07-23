"""Datos compartidos entre suites: una respuesta LLM válida de referencia.

Vive en un módulo propio (no en conftest) para poder importarse
explícitamente desde test_prompts, test_obsidian y test_cli_roundtrip.
"""

from __future__ import annotations

from typing import Any

RESPUESTA_VALIDA: dict[str, Any] = {
    "titulo_unidad": "Régimen portaliano y orden autoritario",
    "resumen_ejecutivo": [
        "La Constitución de 1833 estableció un presidencialismo fuerte tras Lircay.",
        "El Presidente controlaba intendentes, elecciones y facultades extraordinarias.",
        "Las reformas de 1871-1874 iniciaron la parlamentarización que estalló en 1891.",
    ],
    "active_recall": [
        {
            "pregunta": "Explica por qué la Constitución de 1833 concentró poder en el Ejecutivo.",
            "respuesta_modelo": "Tras la victoria conservadora en Lircay se buscó orden y "
            "autoridad impersonal, según la idea portaliana de gobierno obedecido.",
            "pista": "Piensa en qué batalla precede al texto y quién la ganó.",
        },
        {
            "pregunta": "Enumera tres atribuciones del Presidente bajo la carta de 1833.",
            "respuesta_modelo": "Nombrar intendentes y gobernadores, intervenir en "
            "elecciones y ejercer facultades extraordinarias en crisis.",
            "pista": "Una es territorial, una electoral y una de emergencia.",
        },
        {
            "pregunta": "Compara las reformas de 1871-1874 con el resultado de 1891.",
            "respuesta_modelo": "Las reformas limitaron gradualmente al Ejecutivo; 1891 "
            "impuso por las armas la supremacía del Congreso.",
            "pista": "Gradual versus abrupto.",
        },
    ],
    "analogia_feynman": {
        "concepto_original": "Presidencialismo autoritario portaliano",
        "analogia": "Como un edificio donde el administrador elige a los conserjes de "
        "cada piso, cuenta los votos de la junta de vecinos y puede cerrar el edificio "
        "en una emergencia sin preguntar.",
        "donde_se_rompe": "El administrador de un edificio puede ser despedido por la "
        "junta en cualquier momento; el Presidente de 1833 no.",
    },
    "tags_sugeridos": ["historia", "constitucional-chile", "siglo-xix"],
    "dificultad_percibida": "media",
    "aviso_cobertura": None,
}
