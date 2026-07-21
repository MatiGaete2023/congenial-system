# 🧠 Plantilla de Extracción de Conocimiento para TDAH

Sistema automatizado de organización de estudio para **TDAH de presentación
inatenta**, orientado a textos densos de **Derecho e Historia**. Un solo script
de Python sin dependencias obligatorias, con tres módulos:

| Módulo | Qué hace | Comando |
|---|---|---|
| `MicroChunker` | Divide un capítulo en bloques exactos de **15 minutos** | `python extractor_tdah.py chunk capitulo.txt` |
| `GeneradorPrompt` | System Prompt reutilizable para APIs LLM: **3 viñetas + 3 preguntas Active Recall + 1 analogía Feynman** | `python extractor_tdah.py prompt` |
| `ExportadorObsidian` | Vault Markdown completo con tags TDAH (`#baja-energia`, `#bloque-20min`, `#recompensa-dopamina`) | `python extractor_tdah.py vault` |

## Empezar en 2 minutos

```bash
python extractor_tdah.py demo          # los 3 módulos con texto de ejemplo
```

Eso imprime un plan de bloques, muestra el prompt y crea `vault_tdah/` listo
para abrir en Obsidian (instala el plugin **Dataview** para el dashboard).

## Flujo completo con un PDF real

1. `pip install pypdf` (solo si vas a leer PDF directo; con `.txt` no hace falta).
2. `python extractor_tdah.py chunk sentencia.pdf --titulo "Recurso de Protección" --salida "vault_tdah/02 - Derecho/Recurso de Protección"`
3. `python extractor_tdah.py prompt --payload sentencia.pdf > payload.json` — cuerpo
   listo para la Messages API de Anthropic (u otra). La respuesta se valida con
   `GeneradorPrompt.validar_respuesta()` y se vuelca a nota Obsidian con
   `GeneradorPrompt.respuesta_a_markdown()`.
4. Abre el **Dashboard** del vault: él decide qué toca según tu energía actual.

## Por qué esta estructura funciona en un cerebro TDAH

- **Memoria de trabajo reducida** → cada bloque es autocontenido y cabe completo
  en memoria de trabajo (~1210 palabras, máx 5 ideas). Nada exige "recordar lo
  del capítulo anterior": el estado vive en el archivo, no en tu cabeza.
- **Dopamina escasa** → progreso visible (barra `███░░`, contadores X/N) y
  recompensa explícita e inmediata al cierre de cada bloque
  (`#recompensa-dopamina`), pactada *antes* de empezar.
- **Ceguera temporal** → bloques de duración exacta calculada con tu velocidad
  real de lectura (`config_tdah.json`), nunca "estudiar hasta terminar".
- **Fluctuación de energía ejecutiva** → tareas etiquetadas por costo
  (`#baja-energia` / `#alta-energia`): la pregunta deja de ser "¿qué toca?"
  (paraliza) y pasa a ser "¿qué puedo hacer con la energía que tengo AHORA?".
- **Ilusión de competencia al releer** → Active Recall obligatorio (efecto
  testing) y repaso espaciado fijo: 48 h → 7 días → 30 días.

La justificación neurocientífica detallada de cada parámetro está comentada
dentro de `extractor_tdah.py` y `config_tdah.json`.

## Archivos

```
extractor_tdah.py    # script principal (chunker + prompt LLM + vault) — CLI incluida
config_tdah.json     # parámetros calibrados, editables sin tocar código
vault_tdah/          # se genera con `vault` o `demo`; re-ejecutar NUNCA pisa tus notas
```
