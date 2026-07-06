# PLAN MAESTRO DE EJECUCIÓN — Resumidor Jurídico Asistido (RJA)

> Documento generado por auditoría técnica (arquitectura + UX + seguridad).
> Destinatario: una IA ejecutora (Claude Sonnet o equivalente) que trabajará
> tarea por tarea siguiendo el ciclo de `AUTOLOOP.md`.
> Fecha de auditoría: 2026-07-06 · Base: `index.html` @ rama `claude/legal-doc-summarizer-hximuq`.
>
> **ESTADO DE EJECUCIÓN (2026-07-06): T1–T14 COMPLETADAS** (un commit por tarea,
> suite en 52 tests, versión 0.4.0 — ver `CHANGELOG.md`). Queda abierta solo
> **T15 (CSP, opcional)**: requiere prueba manual en navegador con OCR activo
> antes de aplicarse; no ejecutar sin esa verificación.

---

## 0. Contexto (leer antes de tocar nada)

RJA es una aplicación de **un solo archivo** (`index.html`, ~1.800 líneas: CSS +
HTML + JS vanilla) que orquesta el resumen de obras jurídicas extensas usando
Claude/ChatGPT **vía copy-paste manual** (sin APIs). Persistencia en IndexedDB.
Librerías (pdf.js, tesseract, mammoth, transformers/Whisper) se cargan perezosamente
desde CDN o desde `vendor/` local. Tests de funciones puras en `tests/run.mjs`
(Node, sin dependencias), CI en `.github/workflows/`.

## 1. Reglas inquebrantables

1. **Un solo archivo**: toda la app vive en `index.html`. No introducir bundlers,
   frameworks, npm dependencies de runtime ni archivos JS/CSS separados.
2. **Cero red obligatoria**: nada de APIs, telemetría, fuentes remotas ni fetch
   automático. Las únicas descargas permitidas son las librerías lazy ya existentes.
3. **Sin `</script>` literal** dentro del JS embebido (usar `<\/script>`): un literal
   rompe el parser HTML. Ya ocurrió; no repetirlo.
4. **Compatibilidad con los tests**: `tests/run.mjs` extrae funciones por nombre con
   un contador de llaves (`grabFn`). Prohibido usar parámetros con default `{}` u
   objetos literales desbalanceados en la firma de funciones puras testeadas.
5. **Funciones puras abajo, UI arriba**: la lógica testeable (parser, BM25, grafo,
   zip, lotes) no debe tocar el DOM ni `P` global; recibir todo por parámetros.
6. **Idioma**: UI, comentarios y commits en español. Tono sobrio, sin anglicismos
   innecesarios.
7. **Ciclo AUTOLOOP**: objetivo → cambio mínimo → `node tests/run.mjs` → corregir
   (máx. 3 iteraciones) → commit atómico con mensaje descriptivo → push.
8. **No romper etapas anteriores**: tras cada tarea, los 30 tests existentes deben
   seguir en verde. Si una tarea exige cambiar un test, justificarlo en el commit.
9. **No** crear pull requests salvo pedido explícito del usuario. Push a la rama
   `claude/legal-doc-summarizer-hximuq`.

## 2. Hallazgos de auditoría (Fase 1 — verificados línea a línea)

| ID | Severidad | Ubicación (aprox.) | Defecto |
|----|-----------|--------------------|---------|
| A1 | ~~Alta~~ **RESUELTO** | `loadFile()`; `loadProject()` | **XSS por `innerHTML`** con `file.name`/`P.fileName` sin escapar. **Corregido en el commit `4c80bb2`** (ambas ocurrencias usan ya `replaceChildren`+`el()`). El único `innerHTML` con plantilla restante (`#structInfo`) interpola solo números — seguro. No rehacer. |
| A2 | **Alta** | `loadFile()` ~L527 | Al cargar un archivo nuevo se resetean `rawText/cleanText/blocks` pero **no** `consolResponse` ni `products`. El proyecto queda en estado incoherente: productos del documento anterior accesibles/exportables con el nombre del nuevo. |
| A3 | Media | `segment()` ~L833 | Re-segmentar (p. ej. cambiar tamaño de bloque) **descarta silenciosamente** respuestas ya pegadas cuando el capítulo no coincide por índice. Horas de trabajo perdidas sin aviso. |
| A4 | Media | `loadScript()` ~L572 | Dedupe compara `s.src` (URL absoluta) contra rutas relativas: en modo `vendor/` **nunca coincide** y cada extracción re-inyecta el `<script>` de la librería. |
| A5 | Media | `consolidationPrompt()` ~L1120 | No escala: concatena TODOS los parciales. Con 30–50 bloques el prompt supera el límite de entrada del chat. Falta consolidación jerárquica (por lotes → fusión). |
| A6 | Baja | `cleanText()` ~L750 | `/-\n(\w)/` no une palabras cortadas cuya continuación empieza con carácter acentuado o ñ (`\w` es ASCII). |
| A7 | Baja | `buildConceptGraph()` ~L1563 | Coincidencia por subcadena: "acción" co-ocurre falsamente dentro de "transacción". Requiere frontera de palabra. |
| A8 | Baja | `touch()` ~L465; `#btnRagSearch` ~L1610 | `JSON.stringify` del proyecto completo (MBs) en cada autosave; el corpus RAG se re-tokeniza en cada búsqueda. Jank perceptible con libros de 500 pág. |
| A9 | Baja | `normalizeProject()` ~L440 | `{...base,...src}` conserva claves desconocidas del JSON importado (contaminación de estado persistido). |
| A10 | Baja | raíz del repo | Falta `LICENSE` y `CHANGELOG.md`. La versión (0.3.0) no tiene registro de cambios. |

**No son defectos** (verificado, no "corregir"): TDZ de `AUDIO_EXT` (solo se usa
post-parse), `sum` capturado antes de definirse en `renderResponses` (closure válido
al momento del evento), `colspan=6` (la tabla tiene 6 columnas), guardas
`if(!$('#goX'))` (los contenedores se limpian antes).

## 3. Mejoras de valor (Fase 2)

| ID | Área | Propuesta |
|----|------|-----------|
| M1 | UX/responsive | En <900px el sidebar fijo de 230px rompe el layout. Colapsar navegación a barra horizontal scrollable con media query. |
| M2 | Accesibilidad | Añadir `:focus-visible` (outline accent) a botones/inputs; `aria-valuenow/min/max` en las barras de progreso; `aria-expanded` implícito ya cubierto por `<details>`. |
| M3 | UX/navegación | Mostrar progreso vivo en el nav: paso 5 con badge "3/12 respuestas", paso 4 con nº de bloques. Reduce desorientación en obras largas. |
| M4 | Producto | Consolidación jerárquica (resuelve A5): si los parciales superan un presupuesto, generar N prompts de consolidación parcial + 1 prompt de fusión final. Reutilizar `groupIntoLotes`. |
| M5 | Robustez/QA | Smoke test de arranque en `tests/run.mjs`: ejecutar el script completo en un arnés DOM mínimo (Node) y fallar ante `ReferenceError/TypeError` de nivel superior. Ya se usó esta técnica en desarrollo; consolidarla en CI. |
| M6 | Rendimiento | Caché del corpus RAG por hash simple (longitud+primeros chars) y autosave con debounce 1000ms + skip si el JSON no cambió. |
| M7 | Tema claro | `@media (prefers-color-scheme: light)` con paleta alternativa sobre las mismas variables CSS. Bajo riesgo: todo el color ya está en `:root`. |
| M8 | Investigación (opcional) | CSP vía `<meta http-equiv>`: restringir `script-src` a los dos CDNs + `'unsafe-inline'`. **Precaución**: tesseract usa blob workers; probar antes de fijar. No aplicar sin verificar OCR. |

Descartado tras sanity check: búsqueda libre en el texto extraído (el RAG del paso 8
ya lo cubre), migrar el grafo a librería (contradice regla 1), modo multi-archivo
(fuera del alcance del spec).

## 4. Roadmap priorizado (Fase 4 — ejecutar en este orden)

Cada tarea = un ciclo AUTOLOOP = un commit. Formato: objetivo / cambio / criterios de aceptación (CA).

### T1 — ~~Eliminar XSS de nombre de archivo (A1)~~ · YA RESUELTA (commit `4c80bb2`)
- No ejecutar. Verificación opcional: importar un `.json` cuyo `fileName` sea
  `<img src=x onerror=alert(1)>.txt` debe mostrar el nombre literal sin ejecutar nada.

### T2 — Resetear estado derivado al cargar archivo nuevo (A2) · impacto alto, esfuerzo bajo
- **Cambio**: en `loadFile()`, añadir `P.consolResponse=''; P.products=null;` junto al
  reset existente. Si había `products` o respuestas en bloques, pedir `confirm()` antes
  de descartar.
- **CA**: con un proyecto completo, cargar otro archivo → pasos 6–9 vuelven a estar
  bloqueados (`canEnterStep` falla); con Cancel en el confirm no se toca nada.

### T3 — Aviso antes de perder respuestas al re-segmentar (A3) · impacto alto, esfuerzo bajo
- **Cambio**: en `segment()`, antes de reemplazar `P.blocks`, contar respuestas que no
  sobrevivirían (índice/capítulo distinto); si >0, `confirm("Se perderán N respuestas…")`.
- **CA**: re-segmentar con mismo resultado no pregunta; con resultado distinto y
  respuestas existentes pregunta y Cancel aborta sin tocar `P.blocks`.

### T4 — Dedupe correcto en `loadScript` (A4) · impacto medio, esfuerzo bajo
- **Cambio**: comparar con URL absoluta: `const abs=new URL(src,location.href).href;`
  y `[...document.scripts].some(s=>s.src===abs)`.
- **CA**: en modo vendor, dos extracciones seguidas no duplican `<script>` (verificable
  con un test puro si se extrae la lógica, o inspección manual). Tests en verde.

### T5 — Consolidación jerárquica (A5+M4) · impacto alto, esfuerzo medio
- **Cambio**: nueva función pura `consolidationPlan(blocks, maxChars)` → devuelve
  `{mode:'single'|'hierarchical', groups:[...]}` usando `groupIntoLotes` sobre las
  respuestas. UI paso 6: si `hierarchical`, listar prompts de consolidación parcial
  (uno por grupo, con botón copiar) + textareas para pegar cada resultado + prompt
  final de fusión que consume esos resultados parciales.
- **CA**: nuevo test: 40 bloques con respuestas de 3.000 chars y presupuesto 30.000 →
  plan jerárquico con nº de grupos correcto; 5 bloques pequeños → `single`.
  El flujo actual (single) queda intacto.

### T6 — Guiones con acentos en `cleanText` (A6) · esfuerzo mínimo
- **Cambio**: `/-\n([a-záéíóúüñ])/gi` en lugar de `\w`.
- **CA**: nuevo test: `'ju-\nrídica'` → `'jurídica'` y `'eco-\nnómico'` → `'económico'`.

### T7 — Frontera de palabra en el grafo (A7) · esfuerzo bajo
- **Cambio**: en `buildConceptGraph`, en vez de `low.includes(key)`, usar RegExp con
  límites `(^|[^a-z0-9ñ])key([^a-z0-9ñ]|$)` sobre el texto normalizado (escapar el
  concepto con `replace(/[.*+?^${}()|[\]\\]/g,'\\$&')`).
- **CA**: nuevo test: concepto `'acción'` NO co-ocurre con párrafo que solo contiene
  `'transacción'`; el test 13 existente sigue pasando.

### T8 — Rendimiento: autosave y caché RAG (A8+M6) · esfuerzo bajo
- **Cambio**: (a) debounce de `touch()` a 1000ms y comparar el JSON serializado con el
  último guardado (skip si idéntico); (b) memoizar `splitPassages` con clave
  `text.length+':'+text.slice(0,64)`.
- **CA**: dos búsquedas RAG seguidas no re-tokenizan (instrumentable con contador
  temporal en dev); tests en verde; guardado sigue funcionando (badge «Guardado»).

### T9 — Saneo estricto de importación (A9) · esfuerzo bajo
- **Cambio**: `normalizeProject` construye el objeto **solo** con las claves conocidas
  (eliminar el spread `...src`).
- **CA**: nuevo test (extraer `normalizeProject` a pieza pura o testear el objeto
  retornado): importar `{fileName:'x', __proto__ignored:1, junk:'y'}` → el resultado
  no contiene `junk`.

### T10 — Smoke test DOM en CI (M5) · impacto medio, esfuerzo medio
- **Cambio**: en `tests/run.mjs`, arnés con stubs (`document`, `window`, `indexedDB`
  mínimo que devuelve promesas rechazadas controladas, `navigator` por parámetro) que
  ejecuta el `<script>` completo y falla si lanza en el cableado de nivel superior.
- **CA**: `node tests/run.mjs` pasa; introducir a propósito un typo de id
  (`$('#noExiste').addEventListener`) hace fallar la suite (probar y revertir).

### T11 — Responsive + accesibilidad (M1+M2) · esfuerzo bajo
- **Cambio**: media query <900px (nav horizontal con `overflow-x:auto`, `main` a una
  columna); regla global `button:focus-visible,input:focus-visible,select:focus-visible,
  textarea:focus-visible{outline:2px solid var(--accent);outline-offset:2px}`;
  `aria-valuenow` actualizado en `setBar()`.
- **CA**: sin scroll horizontal a 375px de ancho; tab recorre controles con outline
  visible; tests en verde (no tocan CSS).

### T12 — Progreso en navegación (M3) · esfuerzo bajo
- **Cambio**: en `gotoStep`/`updateRespStats`, pintar badge pequeño en los `<li>` del
  nav: paso 4 «N bloques», paso 5 «X/N».
- **CA**: badges correctos al segmentar y al pegar respuestas; sin badge cuando N=0.

### T13 — Tema claro (M7) · esfuerzo medio, riesgo bajo
- **Cambio**: bloque `@media (prefers-color-scheme: light)` redefiniendo las variables
  de `:root` (fondo #f6f8fa, panel #ffffff, texto #1f2328, línea #d0d7de, chip #eaeef2).
  Revisar los 3 colores hardcodeados fuera de variables (`#0d1117` en `pre.out`,
  `#ragResults`, fondo del SVG) y moverlos a variables.
- **CA**: legibilidad AA en ambos temas (contraste ≥4.5:1 texto normal); el SVG del
  grafo sigue legible (mantener su fondo propio si hace falta).

### T14 — LICENSE + CHANGELOG (A10) · esfuerzo mínimo
- **Cambio**: `LICENSE` (MIT, titular: el propietario del repo) y `CHANGELOG.md`
  retroactivo (0.1.0 MVP, 0.2.0 evoluciones RAG/grafo/lotes/Whisper/SRI, 0.3.0 prompts
  específicos + modo adjunto + selector de detalle). Bump a 0.4.0 al cerrar T1–T9.
- **CA**: archivos presentes; `package.json` actualizado; README enlaza CHANGELOG.

### T15 (opcional, al final) — Investigar CSP (M8)
- Solo si T1–T14 están cerradas. Probar en navegador real con OCR activo antes de
  commitear. Si tesseract falla con CSP, documentar el hallazgo en README y NO aplicar.

## 5. Criterios de cierre global

- Los 37 tests previos + los nuevos (T5, T6, T7, T9, T10 añaden ≥5) en verde en CI.
- Nota de contexto: el commit paralelo `4c80bb2` («reforzar consolidacion exhaustiva»)
  cambió el detalle por defecto a **Exhaustivo**, renumeró las reglas del prompt
  (7 = concreción, 8 = citas textuales) y añadió el bloque «EXTENSIÓN MÁXIMA» a la
  consolidación. Cualquier tarea que toque prompts debe partir de ese estado, no del
  descrito en documentación anterior.
- Ninguna regla de la sección 1 violada (verificar especialmente 1, 3 y 4).
- `CHANGELOG.md` refleja cada tarea cerrada.
- Un commit por tarea; mensaje: `fix:`/`feat:`/`test:`/`docs:` + descripción en español.
