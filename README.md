# 🧠 Sistema de Extracción de Conocimiento para TDAH (v2)

Sistema automatizado de organización de estudio para **TDAH de presentación
inatenta**, orientado a textos densos de **Derecho e Historia**. Paquete
Python sin dependencias obligatorias, con suite de tests, invariantes
verificados por hypothesis y CI en cada push.

| Módulo | Qué hace | Comando |
|---|---|---|
| `chunker` | Divide un capítulo en bloques exactos de **15 minutos** | `tdah-estudio chunk capitulo.txt` |
| `prompts` | System Prompt reutilizable para APIs LLM: **3 viñetas + 3 preguntas Active Recall + 1 analogía Feynman** en JSON validado | `tdah-estudio prompt` |
| `obsidian` | Vault Markdown con tags TDAH (`#baja-energia`, `#bloque-20min`, `#recompensa-dopamina`) desde plantillas editables | `tdah-estudio vault` |

## Quickstart (2 minutos)

```bash
pip install .            # o: pip install '.[pdf]' para leer PDF directo
tdah-estudio demo        # los 3 módulos con texto de ejemplo
```

Sin instalar nada también funciona desde el clon del repo:

```bash
PYTHONPATH=src python -m tdah_estudio demo
```

El demo imprime el plan de bloques, muestra el prompt y crea `vault_tdah/`
listo para abrir en Obsidian (instala el plugin **Dataview** para el dashboard).

## Flujo completo con un PDF real

```bash
tdah-estudio chunk sentencia.pdf --titulo "Recurso de Protección" \
    --salida "vault_tdah/02 - Derecho/Recurso de Protección"
tdah-estudio prompt --payload sentencia.pdf > payload.json
```

`payload.json` es el cuerpo listo para la Messages API (el ID de modelo se
configura en `config_tdah.json`, clave `modelo_llm`). La respuesta del LLM
se valida con `prompts.validar_respuesta()` — que acumula todos los errores
de contrato en un solo mensaje — y se convierte en nota Obsidian con
`obsidian.render_sintesis()`.

## Configuración

Todo parámetro de usuario vive en `config_tdah.json`, con su rango válido
documentado al lado. Una clave desconocida o un valor fuera de rango produce
un **aviso por stderr** y cae al valor por defecto: el sistema nunca degrada
en silencio.

## Por qué esta estructura funciona en un cerebro TDAH

- **Memoria de trabajo reducida** → cada bloque cabe completo en memoria de
  trabajo (~1210 palabras, máx 5 ideas) y es autocontenido: el estado vive
  en el archivo, no en tu cabeza.
- **Dopamina escasa** → progreso visible (barra `███░░`, contadores X/N) y
  recompensa explícita e inmediata al cierre de cada bloque, pactada *antes*
  de empezar (`#recompensa-dopamina`).
- **Ceguera temporal** → bloques de duración exacta calculada con tu
  velocidad real de lectura, nunca "estudiar hasta terminar".
- **Fluctuación de energía ejecutiva** → tareas etiquetadas por costo
  (`#baja-energia` / `#alta-energia`): la pregunta deja de ser "¿qué toca?"
  (paraliza) y pasa a ser "¿qué puedo hacer con la energía que tengo AHORA?".
- **Ilusión de competencia al releer** → Active Recall obligatorio (efecto
  testing) y repaso espaciado fijo: 48 h → 7 días → 30 días.

La justificación neurocientífica de cada parámetro está en los docstrings de
`src/tdah_estudio/config.py`, `chunker.py`, `prompts.py` y `obsidian.py`.

## Desarrollo

```bash
pip install -e '.[dev,pdf]'
pytest                        # 59 tests: unitarios, propiedad, golden, round-trip
ruff check . && mypy          # lint + tipos (mismos checks que el CI)
python tests/regenerar_golden.py   # tras cambiar plantillas, revisar diff
```

Estructura:

```
src/tdah_estudio/
├── config.py       # parámetros + carga con avisos (nunca silencio)
├── chunker.py      # troceo puro; invariantes I1-I4 bajo hypothesis
├── prompts.py      # contrato LLM: prompt, payload, validación
├── obsidian.py     # TODO el render, desde plantillas string.Template
├── documentos.py   # .txt/.md/.pdf con errores accionables
├── cli.py          # chunk | prompt | vault | demo
└── plantillas/     # 15 plantillas Markdown editables sin tocar Python
tests/
├── golden/         # contrato visual exacto de las notas generadas
└── fixtures/       # PDF real de 2 páginas + PDF "escaneado"
```
