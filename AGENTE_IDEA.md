# Idea: Automatizar RJA con Claude API / Agentes

## Problema que resuelve

El flujo manual de RJA (copiar prompt → pegar en Claude.ai → copiar respuesta → pegar en RJA) funciona bien
para documentos cortos. Para un texto de 200 páginas con 30–50 bloques, el proceso manual toma 2–3 horas.
Un agente puede completarlo en 5–15 minutos sin intervención.

---

## Arquitectura propuesta

```
proyecto.json (RJA)
       ↓
  rja-agent.mjs          ← script Node.js / Python
       ↓ lee bloques
  Anthropic API           ← claude-sonnet-4-6 o claude-haiku-4-5
       ↓ respuestas
  proyecto_completo.json  ← proyecto RJA listo para abrir en el paso 7
```

El script:
1. Lee el `_proyecto.json` exportado desde el paso 5 de RJA.
2. Envía el prompt de cada bloque a la API de Claude.
3. Guarda las respuestas en el JSON.
4. Opcionalmente consolida automáticamente.
5. Guarda el proyecto listo para abrir en RJA (paso 7 o directamente paso 8).

---

## Implementación Node.js

### Instalación

```bash
npm install @anthropic-ai/sdk
```

### Script: `rja-agent.mjs`

```javascript
import Anthropic from '@anthropic-ai/sdk';
import { readFileSync, writeFileSync } from 'fs';

const MODEL = 'claude-sonnet-4-6';          // o claude-haiku-4-5-20251001 para mayor velocidad
const MAX_TOKENS = 8096;                     // máximo de salida; ajusta según el modelo
const DELAY_MS = 1000;                       // pausa entre llamadas (evitar rate limiting)

const client = new Anthropic();              // usa process.env.ANTHROPIC_API_KEY

// ── Prompts (deben ser idénticos a los de index.html) ──────────────────────
const BLOCK_INSTRUCTIONS = `Eres un asistente jurídico experto. Analiza el siguiente fragmento
de texto jurídico y elabora un resumen profesional EXHAUSTIVO Y DETALLADO.

INSTRUCCIÓN DE EXTENSIÓN (obligatoria):
• El resumen debe tener entre el 20 % y el 50 % de la extensión del fragmento original.
• NO hagas resúmenes cortos ni superficiales.

Estructura exacta:

### CAPÍTULO / SECCIÓN
[nombre]

### RESUMEN ANALÍTICO
[resumen detallado]

### CONCEPTOS CLAVE
- [concepto]: [definición]

### SÍNTESIS
[3-5 oraciones]

Mantén precisión jurídica. Incluye artículos y referencias normativas cuando aparezcan.`;

const CONSOLIDATION_PROMPT = `Eres un asistente jurídico experto. Consolida los resúmenes parciales
en un dossier profesional COMPLETO, EXTENSO Y RIGUROSO.

El RESUMEN MAESTRO debe tener entre el 20 % y el 50 % de la longitud total de los resúmenes recibidos.

Estructura exacta (NO OMITIR NINGUNA SECCIÓN):

## FICHA BIBLIOGRÁFICA
- Título:
- Autor:
- Año:
- Editorial:
- Materia:

## SÍNTESIS EJECUTIVA
1. [punto 1 — 2-3 oraciones]
...

## ÍNDICE TEMÁTICO
- [tema]

## RESUMEN MAESTRO
[resumen integral por capítulos — usa ## y ### para secciones]

## CONCEPTOS CLAVE
- [concepto]: [definición]

## PALABRAS CLAVE
[12-20 palabras clave separadas por comas]`;

// ── Funciones ───────────────────────────────────────────────────────────────
async function resumeBlock(block) {
  const prompt = `${BLOCK_INSTRUCTIONS}\n\n---\n\nBLOQUE ${block.index}: ${block.chapter}\n\n${block.text}`;
  const response = await client.messages.create({
    model: MODEL,
    max_tokens: MAX_TOKENS,
    messages: [{ role: 'user', content: prompt }],
  });
  return response.content[0].text;
}

async function consolidate(blocks) {
  const resps = blocks
    .filter(b => !b.excluded && b.response?.trim())
    .map(b => `\n\n=== BLOQUE ${b.index}: ${b.chapter} ===\n${b.response}`)
    .join('');
  const prompt = CONSOLIDATION_PROMPT + '\n\n---\n\nRESÚMENES PARCIALES:' + resps;
  const response = await client.messages.create({
    model: MODEL,
    max_tokens: MAX_TOKENS,
    messages: [{ role: 'user', content: prompt }],
  });
  return response.content[0].text;
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// ── Main ────────────────────────────────────────────────────────────────────
const [,, inputPath, outputPath] = process.argv;
if (!inputPath) {
  console.error('Uso: node rja-agent.mjs proyecto.json [salida.json]');
  process.exit(1);
}

const project = JSON.parse(readFileSync(inputPath, 'utf-8'));
const output = outputPath || inputPath.replace('.json', '_completo.json');

const pending = project.blocks.filter(b => !b.excluded && !b.response?.trim());
console.log(`Bloques pendientes: ${pending.length} / ${project.blocks.length}`);

// Resumir bloques
for (const block of pending) {
  console.log(`[${block.index}/${project.blocks.length}] Resumiendo: ${block.chapter}`);
  try {
    block.response = await resumeBlock(block);
    console.log(`  ✓ ${block.response.length} chars`);
  } catch (err) {
    console.error(`  ✗ Error: ${err.message}`);
  }
  await sleep(DELAY_MS);
}

// Consolidar
console.log('\nConsolidando...');
try {
  project.consolResponse = await consolidate(project.blocks);
  console.log(`✓ Consolidación: ${project.consolResponse.length} chars`);
} catch (err) {
  console.error(`✗ Error en consolidación: ${err.message}`);
}

project._modified = Date.now();
writeFileSync(output, JSON.stringify(project, null, 2));
console.log(`\n✓ Proyecto guardado en: ${output}`);
console.log('  Ábralo en RJA (paso 1 → Cargar proyecto) y continúe desde el paso 8.');
```

### Uso

```bash
# 1. Exporte el proyecto desde RJA (paso 5 o posterior) → genera "documento_proyecto.json"
# 2. Configure la API key:
export ANTHROPIC_API_KEY="sk-ant-..."

# 3. Ejecute el agente:
node rja-agent.mjs documento_proyecto.json

# 4. Abra el archivo generado en RJA:
#    Paso 1 → Cargar proyecto → seleccione "documento_proyecto_completo.json"
#    Continúe desde el paso 8 (Construir productos)
```

---

## Implementación Python

```python
import anthropic, json, time, sys

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 8096

client = anthropic.Anthropic()  # usa ANTHROPIC_API_KEY del entorno

# (pegar aquí las constantes BLOCK_INSTRUCTIONS y CONSOLIDATION_PROMPT de arriba)

def resume_block(block: dict) -> str:
    prompt = f"{BLOCK_INSTRUCTIONS}\n\n---\n\nBLOQUE {block['index']}: {block['chapter']}\n\n{block['text']}"
    response = client.messages.create(
        model=MODEL, max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text

def consolidate(blocks: list) -> str:
    resps = "".join(
        f"\n\n=== BLOQUE {b['index']}: {b['chapter']} ===\n{b['response']}"
        for b in blocks if not b.get("excluded") and b.get("response", "").strip()
    )
    prompt = CONSOLIDATION_PROMPT + "\n\n---\n\nRESÚMENES PARCIALES:" + resps
    response = client.messages.create(
        model=MODEL, max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text

input_path = sys.argv[1] if len(sys.argv) > 1 else None
if not input_path:
    sys.exit("Uso: python rja-agent.py proyecto.json")

with open(input_path) as f:
    project = json.load(f)

pending = [b for b in project["blocks"] if not b.get("excluded") and not b.get("response", "").strip()]
print(f"Bloques pendientes: {len(pending)}/{len(project['blocks'])}")

for block in pending:
    print(f"[{block['index']}] {block['chapter']}")
    try:
        block["response"] = resume_block(block)
        print(f"  ✓ {len(block['response'])} chars")
    except Exception as e:
        print(f"  ✗ {e}")
    time.sleep(1)

print("\nConsolidando...")
project["consolResponse"] = consolidate(project["blocks"])
print(f"✓ {len(project['consolResponse'])} chars")

output_path = input_path.replace(".json", "_completo.json")
with open(output_path, "w") as f:
    json.dump(project, f, ensure_ascii=False, indent=2)
print(f"\n✓ Guardado: {output_path}")
```

---

## Extensión: Agente con Claude Code

Si tiene acceso a **Claude Code** (CLI), puede orquestar el flujo completo desde la terminal:

```bash
# En la misma carpeta que index.html y el proyecto:
claude -p "Lee el archivo proyecto.json, resume cada bloque usando la API de Claude \
con el prompt de blockInstructions de index.html, consolida las respuestas con \
el consolidationPrompt, y guarda el resultado en proyecto_completo.json"
```

Claude Code puede leer el código fuente de `index.html`, extraer los prompts exactos,
llamar a la API con `mcp__anthropic__*` tools, y devolver el proyecto listo.

---

## Consideraciones prácticas

| Aspecto | Detalle |
|---|---|
| **Modelo recomendado** | `claude-sonnet-4-6` para calidad; `claude-haiku-4-5` para velocidad/costo |
| **Costo estimado** | ~$0.01–$0.05 por bloque (varía según tamaño y modelo) |
| **Rate limiting** | Espere 1–2 s entre llamadas; use `max_tokens=8096` para respuestas completas |
| **Tokens de salida** | Aumente `max_tokens` si los resúmenes se cortan (máx. 8 096 en Sonnet) |
| **Privacidad** | El texto completo del documento se envía a Anthropic; verifique sus políticas |
| **Retries** | Agregue lógica de retry para errores 529 (sobrecarga) con backoff exponencial |
| **Archivo final** | El `.json` resultante es compatible con RJA sin modificaciones |

---

## Integración con Claude Code en la web (sin servidor)

Si usa **Claude Code en la web** (code.claude.com), puede adjuntar el `_proyecto.json`
directamente en la sesión y pedir:

> *"Resume cada bloque de este proyecto RJA usando la API de Anthropic, consolida
> las respuestas siguiendo el consolidationPrompt del README, y devuélveme el
> proyecto_completo.json listo para abrir en RJA."*

Claude Code tiene acceso a la API de Anthropic desde el entorno remoto y puede
completar el proceso sin que usted escriba ningún script.
