---
tipo: sistema
tags: [sistema]
---

# 04 · Síntesis LLM

Aquí viven las notas generadas con el System Prompt (resumen 3 viñetas +
3 preguntas Active Recall + analogía Feynman).

Flujo: PDF → `tdah-estudio prompt --payload doc.pdf` → API del LLM →
`prompts.validar_respuesta()` → `obsidian.render_sintesis()` → esta carpeta.

Regla: una síntesis por unidad temática. Si el LLM avisó `aviso_cobertura`,
crea otra unidad para lo que quedó fuera — no lo dejes implícito, tu yo
de la semana del examen no lo recordará.
