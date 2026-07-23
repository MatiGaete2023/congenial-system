"""Sistema de Extracción de Conocimiento para TDAH inatento (v2).

Paquete con tres módulos de dominio y dos de soporte:

- ``config``     : parámetros calibrados neurocognitivamente, carga con avisos.
- ``chunker``    : lógica PURA de troceo en bloques de 15 minutos (sin I/O,
                   sin Markdown — la separación permite testear invariantes
                   con hypothesis sin tocar disco).
- ``prompts``    : contrato con el LLM (system prompt, payload, validación).
- ``obsidian``   : TODO el renderizado Markdown (bloques, síntesis, vault)
                   desde plantillas externas ``string.Template``.
- ``documentos`` : lectura de .txt/.md/.pdf y texto de demostración.
- ``cli``        : orquestación de los anteriores.
"""

__version__ = "2.0.0"
