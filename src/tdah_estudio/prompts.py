"""Contrato con el LLM: system prompt, payload y validación de respuesta.

Este módulo NO renderiza Markdown (eso vive en ``obsidian.py``) y NO llama
a ninguna red: produce el payload y valida lo que vuelve. Mantenerlo puro
permite testear el contrato completo sin mocks de HTTP.

DISEÑO DEL PROMPT — cada decisión y su razón neurocognitiva:

* Salida en JSON estricto: la estructura fija permite volcar la respuesta
  a la plantilla Obsidian sin reformateo manual (cero fricción post-proceso;
  cada paso manual repetido es una oportunidad de abandono del sistema).
* Exactamente 3 viñetas / 3 preguntas / 1 analogía: los límites duros
  existen porque "resume esto" sin cota produce muros de texto que
  reintroducen el problema original. 3 elementos caben en una memoria de
  trabajo TDAH (4±1 chunks, extremo bajo); 7 no.
* Viñetas de máximo 25 palabras: una viñeta que hay que releer no es una
  viñeta, es un párrafo disfrazado.
* Preguntas de RECUPERACIÓN y no de reconocimiento: el efecto testing
  (Roediger & Karpicke, 2006) muestra que intentar recuperar consolida la
  memoria a largo plazo mucho más que releer. En TDAH además convierte el
  repaso pasivo (donde la mente se fuga) en tarea activa con feedback
  inmediato: micro-dopamina por acierto.
* Analogía Feynman con objeto cotidiano + campo "dónde se rompe": la
  codificación dual crea una ruta de recuperación alternativa cuando el
  término técnico no aparece; el campo "dónde se rompe" evita que la
  analogía se generalice de más en el examen.
"""

from __future__ import annotations

import json
from typing import Any

from tdah_estudio.config import ConfigTDAH

VERSION_PROMPT = "2.0.0"


def system_prompt(materia: str = "Derecho e Historia", idioma: str = "español") -> str:
    """System prompt completo, parametrizado y listo para cualquier API.

    Parametrizar (materia, idioma) en vez de editar a mano existe porque
    editar prompts manualmente cada vez es fricción repetitiva: cada
    decisión evitada es capacidad ejecutiva conservada para estudiar.
    """
    return f"""\
Eres "Procesador de Estudio TDAH v{VERSION_PROMPT}", un asistente experto en
pedagogía para estudiantes con TDAH de presentación inatenta y en análisis de
textos académicos de {materia}. Trabajas siempre en {idioma}.

== TU TAREA ==
Recibirás el texto de un documento extenso y denso (capítulo, sentencia, ley,
manual). Debes transformarlo en una unidad de estudio apta para memoria de
trabajo reducida. Tu salida se inserta automáticamente en una plantilla, por
lo que el formato es OBLIGATORIO e innegociable.

== REGLAS DE PROCESAMIENTO ==
1. Lee el documento completo antes de escribir nada.
2. Identifica las 3 ideas con mayor probabilidad de aparecer en un examen
   (criterio: definiciones operativas, fechas-bisagra, requisitos/elementos
   de instituciones jurídicas, relaciones causa-efecto históricas).
3. Ignora por completo: notas al pie ornamentales, citas de cortesía,
   digresiones del autor. El estudiante NO puede permitirse ruido.
4. Nunca uses frases de relleno ("es importante destacar", "cabe señalar").
   Cada palabra que no informa, estorba.
5. Si el documento excede una unidad temática coherente, procesa SOLO la
   principal e indícalo en "aviso_cobertura".

== FORMATO DE SALIDA (JSON estricto, sin texto fuera del JSON) ==
{{
  "titulo_unidad": "máximo 8 palabras, sin subtítulos",
  "resumen_ejecutivo": [
    "Viñeta 1: la tesis central del documento. Máximo 25 palabras.",
    "Viñeta 2: el mecanismo, requisito o proceso clave. Máximo 25 palabras.",
    "Viñeta 3: la consecuencia, excepción o dato-bisagra. Máximo 25 palabras."
  ],
  "active_recall": [
    {{
      "pregunta": "Pregunta de RECUPERACIÓN (empieza con Explica/Enumera/Compara/Por qué). Prohibido verdadero-falso y opción múltiple.",
      "respuesta_modelo": "Respuesta completa en máximo 40 palabras.",
      "pista": "Pista de una frase para desbloqueo sin revelar la respuesta."
    }},
    {{ "pregunta": "...", "respuesta_modelo": "...", "pista": "..." }},
    {{ "pregunta": "...", "respuesta_modelo": "...", "pista": "..." }}
  ],
  "analogia_feynman": {{
    "concepto_original": "El concepto más abstracto del documento.",
    "analogia": "Explicación con un objeto/situación de la vida doméstica cotidiana (cocina, edificio, fútbol, supermercado). Máximo 60 palabras. Sin tecnicismos: si un niño de 12 años no lo entiende, reescríbela.",
    "donde_se_rompe": "Una frase: en qué punto la analogía deja de ser fiel al concepto real (evita falsas generalizaciones en el examen)."
  }},
  "tags_sugeridos": ["derecho|historia", "y 2-4 tags temáticos en kebab-case"],
  "dificultad_percibida": "baja|media|alta",
  "aviso_cobertura": "null, o qué parte del documento quedó fuera y por qué"
}}

== CRITERIOS DE CALIDAD (autoverifica antes de responder) ==
- ¿Cada viñeta sobrevive sola, sin las otras dos? Debe hacerlo.
- ¿Las 3 preguntas cubren las 3 viñetas (una por viñeta)? Deben hacerlo.
- ¿La analogía usa SOLO vocabulario cotidiano? Debe hacerlo.
- ¿El JSON es parseable? Verifica comillas y comas antes de emitir.
"""


def payload_api(
    cfg: ConfigTDAH, texto_documento: str, materia: str = "Derecho e Historia"
) -> dict[str, Any]:
    """Payload listo para la Messages API de Anthropic (u homóloga).

    El ID de modelo viene de la configuración (restricción 5 del proceso:
    nada de valores de usuario hardcodeados). max_tokens generoso porque el
    JSON de salida ronda 600-900 tokens; temperature 0.2 porque queremos
    extracción fiel, no creatividad — la única sección "creativa" es la
    analogía y el prompt ya la acota estructuralmente.
    """
    return {
        "model": cfg.modelo_llm,
        "max_tokens": 2048,
        "temperature": 0.2,
        "system": system_prompt(materia=materia),
        "messages": [
            {
                "role": "user",
                "content": (
                    "Procesa el siguiente documento según tus reglas y "
                    "devuelve únicamente el JSON:\n\n<documento>\n"
                    f"{texto_documento}\n</documento>"
                ),
            }
        ],
    }


def validar_respuesta(json_crudo: str) -> dict[str, Any]:
    """Valida la respuesta del LLM contra el contrato del prompt.

    Acumula TODOS los errores y falla con mensajes accionables (qué campo,
    qué se esperaba): si el pipeline se rompe con un error críptico, el
    estudiante pierde la sesión de estudio depurando — el peor resultado
    posible para TDAH. Un error accionable se arregla reintentando la
    llamada; uno críptico se arregla abandonando el sistema.
    """
    try:
        datos = json.loads(json_crudo)
    except json.JSONDecodeError as exc:
        raise ValueError(f"El LLM no devolvió JSON válido: {exc}") from exc
    if not isinstance(datos, dict):
        raise ValueError("El LLM devolvió JSON que no es un objeto")

    errores: list[str] = []

    if not str(datos.get("titulo_unidad", "")).strip():
        errores.append("falta 'titulo_unidad'")

    resumen = datos.get("resumen_ejecutivo")
    if not isinstance(resumen, list) or len(resumen) != 3:
        errores.append("'resumen_ejecutivo' debe ser lista de exactamente 3 viñetas")
    else:
        for i, v in enumerate(resumen, 1):
            # Margen de 30 sobre las 25 pactadas: tolerancia sí, muros de texto no.
            if len(str(v).split()) > 30:
                errores.append(f"viñeta {i} excede 30 palabras")

    recall = datos.get("active_recall")
    if not isinstance(recall, list) or len(recall) != 3:
        errores.append("'active_recall' debe ser lista de exactamente 3 preguntas")
    else:
        for i, q in enumerate(recall, 1):
            for campo in ("pregunta", "respuesta_modelo", "pista"):
                if not isinstance(q, dict) or not str(q.get(campo, "")).strip():
                    errores.append(f"pregunta {i}: falta campo '{campo}'")

    feynman = datos.get("analogia_feynman")
    if not isinstance(feynman, dict):
        errores.append("falta 'analogia_feynman'")
    else:
        for campo in ("concepto_original", "analogia", "donde_se_rompe"):
            if not str(feynman.get(campo, "")).strip():
                errores.append(f"analogia_feynman: falta campo '{campo}'")

    if errores:
        raise ValueError("Respuesta LLM fuera de contrato: " + "; ".join(errores))
    return datos
