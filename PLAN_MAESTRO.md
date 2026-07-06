# PLAN MAESTRO DE EJECUCIÓN — RJA v0.3 → v0.4

> **Destinatario:** IA ejecutora (Claude Sonnet 4.6 / Sonnet 5 u otra).
> **Origen:** Auditoría multidimensional (arquitectura, seguridad, UX/UI, procesos) realizada sobre el commit `2a0eade`.
> **Método de trabajo obligatorio:** ejecutar las tareas EN ORDEN de prioridad (P0 → P3). Después de CADA tarea: `npm test` debe dar 0 fallidas. Commit atómico por tarea con mensaje descriptivo en español.

---

## 0. CONTEXTO DEL PROYECTO (leer antes de tocar nada)

RJA (Resúmenes Jurídicos Asistidos) es una aplicación de **un solo archivo** `index.html` (vanilla JS, sin dependencias, sin build) que ayuda a resumir documentos jurídicos: extrae texto → limpia → segmenta en bloques → genera prompts que el usuario lleva manualmente a Claude.ai/ChatGPT → recibe respuestas → consolida → exporta DOCX/MD/ZIP generados desde cero (sin librerías).

Archivos:
- `index.html` — toda la aplicación (CSS + HTML + JS en un archivo).
- `manual.html` — manual de usuario.
- `tests/run.mjs` — 67 tests Node.js que evalúan el `<script>` de index.html vía `eval()`.
- `README.md`, `AGENTE_IDEA.md` — documentación.

### Peculiaridad crítica del harness de tests
`tests/run.mjs` hace `eval(script)` en scope de módulo ESM. `let P = blankProject()` crea un binding local del eval; `Object.assign(globalThis, {P})` comparte **el mismo objeto**. Consecuencia: en los tests **MUTAR `P` funciona** (`P.blocks = [...]`, `P.sensitive = true`), **REEMPLAZAR no** (`globalThis.P = otro` no lo ven las funciones). Nunca reasignar `P` en tests.

---

## 1. REGLAS INQUEBRANTABLES (violarlas = tarea rechazada)

| # | Regla |
|---|---|
| R-1 | Un solo archivo `index.html`. Sin frameworks, sin bundler, sin npm deps de runtime, sin `import` en el script del navegador. |
| R-2 | 100 % local por defecto: cero peticiones de red automáticas. CDN solo tras clic explícito del usuario (`loadVendorLibs`). |
| R-3 | Los **encabezados de sección** de los prompts (`## FICHA BIBLIOGRÁFICA`, `## SÍNTESIS EJECUTIVA`, `## ÍNDICE TEMÁTICO`, `## RESUMEN MAESTRO`, `## CONCEPTOS CLAVE`, `## PALABRAS CLAVE`; `### CAPÍTULO / SECCIÓN`, `### RESUMEN ANALÍTICO`, `### CONCEPTOS CLAVE`, `### SÍNTESIS`) son consumidos por `parseConsolidation()` y `validateResponse()`. NO renombrarlos. El texto interno de instrucciones sí puede ajustarse. |
| R-4 | La instrucción de extensión 20 %–50 % + máxima salida + Artifact/Canvas en ambos prompts es requisito del propietario. No eliminarla ni suavizarla. |
| R-5 | Modo Material Sensible: ningún cambio puede crear una vía por la que texto del documento salga hacia IA con `P.sensitive === true`. Todo botón nuevo que copie/exporte prompts lleva `data-ia-guard` y pasa por `sensitiveGuardIA()`. |
| R-6 | Marcadores `[p. N]` y `[[RJA_BLOCK_ID]]` siguen siendo opt-in y desactivados por defecto. |
| R-7 | Idioma de UI, comentarios y commits: español. |
| R-8 | Compatibilidad: navegadores evergreen (Chrome/Firefox/Edge/Safari últimos 2 años). Sin sintaxis que Node 18 no ejecute (los tests evalúan el mismo script). |
| R-9 | Tests: nunca borrar tests existentes; solo añadir (T-68 en adelante) o corregir aserciones si la tarea cambia el comportamiento documentadamente. `npm test` → 0 fallidas antes de cada commit. |
| R-10 | Toda función nueva usada por tests se añade al bloque `Object.assign(globalThis, {...})` del final del script. |

---

## 2. HALLAZGOS DE AUDITORÍA (Fase 1 — verificados contra el código)

Severidad: **S1** = seguridad/crash, **S2** = lógica/datos incorrectos, **S3** = inconsistencia/UX menor.

| ID | Sev | Ubicación (función) | Defecto verificado |
|----|-----|----------------------|--------------------|
| H-01 | S1 | Listener de `btnBm25` (~línea 1464) | **XSS**: `el.innerHTML = ...${r.text.slice(0,200)}...` inyecta texto del documento SIN escapar. Un `.txt`/`.md` malicioso con `<img src=x onerror=...>` ejecuta JS al buscar. |
| H-02 | S1 | `xmlEsc()` + `renderBlockStructure()` | **Inyección de atributo**: `xmlEsc` no escapa `"` ni `'`, pero se usa en `value="${xmlEsc(b.chapter)}"`. Un título de capítulo derivado del documento con `"` rompe el atributo y permite inyectar `onfocus=...`. |
| H-03 | S1 | Listener de `fileInput` | `fileInfo.innerHTML` interpola `file.name` sin escapar. Nombre de archivo `<img src=x onerror=...>.txt` ejecuta JS. |
| H-04 | S1 | `normalizeProject()` + `buildDocxXml()`/`buildMarkdown()` | `normalizeProject` acepta cualquier objeto como `products` (p. ej. `{}`). `buildDocxXml` hace `const f=pr.ficha;` y luego `f.title` → **TypeError** al exportar. `canEnterStep(9)` considera `{}` truthy, así que el crash es alcanzable cargando un `.json` editado. |
| H-05 | S1 | (ausencia global) | **Pérdida total de trabajo**: no existe `localStorage`, autosave ni `beforeunload`. Cerrar la pestaña tras 2 horas de copy-paste manual pierde todo. Es el defecto de mayor impacto real para el usuario. |
| H-06 | S2 | `ensurePdfWorker()` | `VENDOR.pdfWorker || VENDOR.pdfWorkerLocal`: el primer operando siempre es truthy → el fallback local NUNCA se usa. Con librerías locales y sin internet, el worker apunta al CDN y la extracción PDF falla. Contradice el modo "totalmente local" del README. |
| H-07 | S2 | `detectChapters()` patrón TODO-MAYÚSCULAS | `/^[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]{3,59}[A-ZÁÉÍÓÚÑ]$/` matchea CUALQUIER línea en mayúsculas de 5–61 chars. Los textos jurídicos abundan en ellas (VISTOS, CONSIDERANDO, nombres de partes) → sobre-segmentación masiva: decenas de bloques minúsculos. |
| H-08 | S2 | `gotoStep(7)` | `totalChars` suma respuestas de TODOS los bloques, incluidos los excluidos, mientras `buildBatchConsolPrompts()` los filtra → el aviso de lotes puede mostrarse/calcularse mal. |
| H-09 | S2 | `btnExportPrompts`, `btnExportAllPrompts`, `buildPackageZip` | Los tres exportan prompts de bloques **excluidos** (`P.blocks.map(...)` sin filtrar `!b.excluded`), incoherente con la semántica de exclusión. |
| H-10 | S2 | `validateResponse()` | Umbral de "muy corta" = 4 % del bloque. Incoherente con la regla de negocio nueva 20 %–50 %: una respuesta del 6 % pasa como ✓. |
| H-11 | S3 | `buildObsidian()` | Valores YAML entre comillas dobles usan `xmlEsc`, que no escapa `"` → un título con comillas rompe el frontmatter YAML. |
| H-12 | S3 | Listener de `btnSaveConsol` | Con textarea vacío: guarda `''`, toast "Consolidación guardada", luego `gotoStep(8)` falla y lanza segundo toast contradictorio. |
| H-13 | S3 | `saveBlockResp()` | El pill de estado ✓/⚠/✗ no se actualiza al escribir; solo al re-entrar al paso 6. (No re-renderizar en `oninput` — se perdería el foco; actualizar solo el pill del bloque.) |
| H-14 | S3 | `_zipFromBytes()` | Flag EFS (bit 11, UTF-8) no seteado y fecha/hora DOS = 0. Latente (nombres actuales son ASCII), pero frágil. |
| H-15 | S3 | `manual.html` vs `index.html` | Versión inconsistente: "v0.3" vs "v0.3.0". |
| H-16 | S3 | `extractTxt()` | Fuerza UTF-8; archivos Latin-1 se corrompen silenciosamente. |

**Cumplimiento de reglas existentes:** los invariantes del README se cumplen tras el commit `2a0eade` (prompts: estructura estable ✓; 100 % local ✓; opt-in ✓). No hay APIs de pago en la app. Sin violaciones activas — los hallazgos son defectos, no incumplimientos normativos.

---

## 3. MEJORAS DE VALOR (Fase 2 — filtradas por el sanity check)

Descartadas por baja relación valor/esfuerzo o conflicto con R-1/R-2: PWA/manifest, modo oscuro completo (diferido a P3 opcional), migración a módulos, virtual-DOM. Lo que sigue sobrevivió dos pasadas de revisión:

- **M-01 — Indicador de ratio 20–50 % por bloque**: la regla de negocio ya vive en los prompts; la UI debe medirla. Mostrar `respuesta/fragmento = NN %` con color (rojo <15 %, ámbar 15–20 % o >55 %, verde 20–55 %). Es la mejora que más refuerza el requisito del propietario.
- **M-02 — Autosave + restauración** (resuelve H-05; detalles en tarea).
- **M-03 — Barra de progreso del paso 6**: "Respondidos 4/12 · 31.200 chars" + botón **"Copiar siguiente prompt pendiente"** (reduce la fricción del loop copiar/pegar, que es el 80 % del tiempo de uso).
- **M-04 — Sistema de diseño con tokens CSS**: variables `--c-*`, `--sp-*`, `--radius` en `:root`; estados `:focus-visible`; toast con variantes éxito/error; pills de estado con texto además de color (accesibilidad daltónica).
- **M-05 — Accesibilidad**: `aria-live="polite"` en `#toast`, `aria-label` en botones de icono, `title`+texto en indicadores de color, contraste AA en `.stat-pill` y textos `#666` → `#555`.
- **M-06 — Drag & drop de archivo en paso 1** + Enter dispara búsqueda BM25.
- **M-07 — CI**: GitHub Action que ejecuta `npm test` en cada push/PR (el proyecto no tiene ninguna verificación automática remota).

---

## 4. ROADMAP PRIORIZADO — TAREAS EJECUTABLES

Formato de cada tarea: **Objetivo / Cambios / Criterios de aceptación (CA) / Tests nuevos**.
Los números de línea son orientativos; localizar siempre por nombre de función.

---

### ⛔ P0 — Seguridad y pérdida de datos (bloqueantes)

#### TAREA 1 — Neutralizar XSS (H-01, H-02, H-03, H-11)
**Cambios en `index.html`:**
1. Extender `xmlEsc` para escapar también comillas: añadir `.replace(/"/g,'&quot;').replace(/'/g,'&#39;')`. (Verificado: T-43 y T-57 no lo contradicen.)
2. Listener `btnBm25`: extraer helper puro `bm25ResultHtml(r)` que devuelva el HTML del resultado con `xmlEsc(r.text.slice(0,200))`, y usarlo en el listener. Exportar el helper a `globalThis` (R-10).
3. Listener `fileInput`: `xmlEsc(file.name)` en el innerHTML de `fileInfo`.
4. `buildObsidian`: en los valores YAML, sustituir `xmlEsc(...)` por una sanitización YAML: `String(v||'').replace(/"/g,"'")` (helper `yamlSafe`). Nota: `xmlEsc` con `&quot;` NO sirve para YAML (mostraría la entidad literal).
**CA:** ningún `innerHTML` del archivo interpola texto de documento/archivo/respuesta sin pasar por `xmlEsc` (auditar con `grep -n 'innerHTML' index.html` una a una); `npm test` 0 fallidas.
**Tests:** T-68 `xmlEsc` escapa `"` y `'`; T-69 `bm25ResultHtml({score:1,text:'<img src=x onerror=a>'})` no contiene `<img`; T-70 `buildObsidian` con título `A "B"` produce YAML sin comilla doble interna.

#### TAREA 2 — Blindar `products` malformado (H-04)
**Cambios:** en `normalizeProject`, reemplazar la asignación laxa de `products` por normalización estricta: si `obj.products` es objeto → construir `{ficha:{...9 campos string},synthLines:[],indexItems:[],master:'',concepts:[],keywords:[]}` completando tipos; si no → `null`. En `buildDocxXml` y `buildMarkdown`, defensas locales: `const pr=P.products||{}; const f=pr.ficha||{};`.
**CA:** cargar un proyecto con `"products": {}` y exportar DOCX/MD no lanza excepción.
**Tests:** T-71 `normalizeProject({products:{}})` → products con todas las claves; T-72 con ese P mutado, `buildMarkdown()` y `buildDocxXml()` no lanzan.

#### TAREA 3 — Autosave y restauración (H-05, M-02)
**Cambios:**
1. `persistDraft()`: guarda `JSON.stringify(P)` en `localStorage['rja_draft_v1']`, debounced 2 s, llamado desde `touch()`. Envolver en `try/catch` (QuotaExceeded → toast de advertencia una sola vez).
2. **Excepción de privacidad (R-5):** si `P.sensitive === true`, NO persistir y además `localStorage.removeItem('rja_draft_v1')`. Al activar el toggle sensible, purgar el draft existente.
3. Al cargar (`DOMContentLoaded`): si existe draft, mostrar banner no-modal "Hay una sesión anterior del DD/MM hh:mm — [Restaurar] [Descartar]". Restaurar = `P = normalizeProject(JSON.parse(draft))` + `updateSensitiveUI()` + `loadMetaForm()` + `refreshNav()`. Nota: en navegador `P` es reasignable sin problema (la restricción de no-reemplazo aplica solo a tests).
4. `beforeunload`: si `P._modified` posterior al último persist y hay contenido (`P.rawText || P.blocks.length`), `e.preventDefault()`.
5. Botón "Borrar datos locales" en paso 1 (junto a Nuevo proyecto) que purga el draft. "Nuevo proyecto" también lo purga.
6. Documentar en `manual.html` (sección modo sensible y FAQ).
**CA:** editar → recargar página → banner aparece → Restaurar recupera bloques y respuestas; con modo sensible ON no se escribe nada en localStorage (verificar en DevTools).
**Tests:** T-73 `persistDraft` (exportada) no escribe cuando `P.sensitive=true` (mock de `globalThis.localStorage` con objeto simple en el test); T-74 escribe cuando no es sensible y el JSON parsea de vuelta a un proyecto normalizable.

#### TAREA 4 — Worker PDF local primero (H-06)
**Cambios:** `ensurePdfWorker()` debe preferir `VENDOR.pdfWorkerLocal` cuando `pdfjsLib` existe pero `workerSrc` está vacío (ese estado solo ocurre con carga manual/local de librerías; `loadVendorLibs` ya setea el CDN en su propio flujo). Orden correcto: local primero, CDN como comentario de alternativa.
**CA:** con `pdf.min.js` y `pdf.worker.min.js` junto al HTML y sin red, la extracción PDF funciona; vía CDN (botón) sigue funcionando.
**Tests:** T-75 `ensurePdfWorker` asigna `pdf.worker.min.js` (local) cuando `globalThis.pdfjsLib={GlobalWorkerOptions:{workerSrc:''}}` está mockeado; limpiar el mock al final del test.

---

### 🔶 P1 — Corrección de lógica y coherencia

#### TAREA 5 — Frenar la sobre-segmentación (H-07)
**Cambios en `segment()`:** post-proceso de fusión: constante `MIN_BLOCK_CHARS = 500`; recorrer los bloques resultantes y fusionar cada bloque con `sizeOf(text) < MIN_BLOCK_CHARS` con el ANTERIOR (concatenando texto con `\n\n` y conservando el chapter del anterior; el primero se fusiona con el siguiente). Reindexar `index` al final (1..N). No tocar `detectChapters` (T-58 depende de él).
**CA:** un texto con 50 líneas TODO-MAYÚSCULAS cortas produce bloques ≥500 chars (salvo que el total sea menor); los tests de segmentación existentes (T-62, T-63, T-64) siguen verdes.
**Tests:** T-76 texto con 30 pseudo-encabezados en mayúsculas y párrafos de 100 chars → `blocks.length` reducido y todos con `sizeOf ≥ 500` excepto a lo sumo el último; T-77 los `index` quedan consecutivos desde 1.

#### TAREA 6 — Semántica de exclusión coherente (H-08, H-09)
**Cambios:**
1. `gotoStep(7)`: `totalChars` con `P.blocks.filter(b=>!b.excluded)`.
2. `btnExportPrompts`, `btnExportAllPrompts` y la entrada `_prompts.md` de `buildPackageZip`: filtrar `!b.excluded`.
**CA:** un bloque excluido no aparece en ningún artefacto de prompts ni infla el aviso de lotes. (Sí sigue apareciendo en `_fragmentos_resumidos.md` y en el JSON — eso es correcto: son registros, no salidas hacia IA.)
**Tests:** T-78 `buildPackageZip` con un bloque excluido → `_prompts.md` del ZIP no contiene su capítulo (reutilizar el patrón de extracción de texto de ZIP de T-63/T-55).

#### TAREA 7 — Validación alineada al 20–50 % (H-10, M-01)
**Cambios:**
1. `validateResponse(b)`: calcular `ratio = r.length / Math.max(1,(b.text||'').length)` y devolverlo en el resultado. Umbrales: `ratio < 0.15` → `{ok:false, reason:'por debajo del objetivo 20 %'}`; `0.15–0.20` o `>0.55` → warn; resto ok. Mantener el mínimo absoluto de 200 chars.
2. `renderResponses()`: pill con el porcentaje (`Math.round(ratio*100)+' %'`) y color según rango (verde/ámbar/rojo).
**CA:** una respuesta del 10 % se marca ✗; una del 30 % muestra pill verde "30 %".
**Tests:** T-79 ratio 0.10 → `ok:false`; T-80 ratio 0.30 → `ok:true` sin warn; T-81 ratio 0.70 → warn. **Atención:** revisar si algún test existente (T-2x de validación) asume el umbral del 4 % y actualizar su aserción documentándolo en el commit.

#### TAREA 8 — Micro-fricciones (H-12, H-13, H-15)
**Cambios:**
1. `btnSaveConsol`: si el textarea está vacío → un solo toast "Pegue la respuesta de consolidación primero" y return (sin guardar ni navegar).
2. `saveBlockResp`: tras guardar, actualizar SOLO el pill de estado de ese bloque (darle `id="blockPill${index}"` en el render y reescribir su texto/clase), sin re-render completo (se perdería el foco del textarea).
3. Unificar versión: "v0.3.0" en `manual.html` (título, header y footer).
**CA:** escribir en el textarea de respuesta actualiza el pill en vivo sin perder el foco; guardar consolidación vacía produce exactamente un toast.
**Tests:** T-82 `validateResponse` sigue siendo pura (sin DOM) — cubierto por T-79–81; el resto es verificación manual (documentar en el commit).

---

### 🔷 P2 — UX, visual y accesibilidad

#### TAREA 9 — Tokens de diseño (M-04)
**Cambios:** definir en `:root`: `--c-primary:#1a6bb5; --c-primary-hover:#155a9a; --c-header:#1a3a5c; --c-danger:#c0392b; --c-surface:#fff; --c-border:#dde; --c-text:#222; --c-text-muted:#555; --radius:4px; --sp-1:4px; --sp-2:8px; --sp-3:12px; --sp-4:16px`. Sustituir los valores hardcodeados del CSS por las variables (solo el CSS; no tocar HTML/JS). Añadir `button:focus-visible, input:focus-visible, textarea:focus-visible { outline:2px solid var(--c-primary); outline-offset:2px }`. Toast: clases `toast-ok` (borde izq. verde) y `toast-err` (rojo) + parámetro opcional en `toast(msg,dur,kind)`.
**CA:** apariencia idéntica salvo focos visibles y toasts con variantes; grep de `#1a6bb5` en el CSS devuelve solo la definición de la variable.
**Tests:** no aplica (CSS); verificación visual manual.

#### TAREA 10 — Progreso y "siguiente pendiente" (M-03)
**Cambios:** en paso 6, sobre `blocksContainer`, un header `id="respProgress"`: "Respondidos X/N · NN.NNN chars" (excluidos fuera del conteo) + botón `data-ia-guard` "Copiar siguiente prompt pendiente" que localiza el primer bloque `!excluded && !response.trim()`, copia su prompt, hace scroll a su card (`scrollIntoView({behavior:'smooth'})`) y la resalta 2 s. Actualizar el header desde `renderResponses()` y `saveBlockResp()`.
**CA:** con 3 de 5 respondidos el header muestra "3/5"; el botón copia el prompt del bloque 4 y navega hasta él; respeta modo sensible (R-5).
**Tests:** T-83 helper puro `nextPendingBlock()` (exportado) devuelve el primer bloque sin respuesta no excluido; T-84 devuelve `null` cuando todos respondidos.

#### TAREA 11 — Accesibilidad y entrada (M-05, M-06)
**Cambios:** `#toast` con `role="status" aria-live="polite"`; `aria-label` en botones de solo icono/emoji; drag & drop en la card del `fileInput` del paso 1 (eventos `dragover`/`drop`, asignar `fileInput.files = e.dataTransfer.files` y disparar `change`); `keydown` Enter en `#bm25Query` dispara la búsqueda; texto `#666` → `#555` en estilos de ayuda.
**CA:** arrastrar un `.txt` sobre la card lo carga; Enter busca en BM25; lectores de pantalla anuncian los toasts.
**Tests:** verificación manual (documentar en commit).

---

### ⚪ P3 — Endurecimiento opcional (solo si las anteriores están verdes)

#### TAREA 12 — Robustez ZIP (H-14)
Setear bit 11 (EFS/UTF-8) en flags del local header y central directory de `_zipFromBytes` (`_u16(0x0800)` en ambos) y una fecha DOS fija válida (p. ej. 2024-01-01: `date=0x5821`, `time=0`). **CA:** `python3 -m zipfile -t` sobre el paquete y sobre el DOCX anidado sigue OK; el DOCX abre en Word/LibreOffice. **Tests:** los tests ZIP existentes (T-01…) siguen verdes; T-85 verifica el flag en los bytes (offset 6–7 del local header = `00 08`).

#### TAREA 13 — CI (M-07)
Crear `.github/workflows/test.yml`: `on: [push, pull_request]`, Node 20, `npm test`. **CA:** el workflow pasa en el push.

#### TAREA 14 — Codificación de TXT (H-16)
En `extractTxt`, si el resultado UTF-8 contiene ≥ N caracteres U+FFFD, reintentar lectura como `windows-1252` (`TextDecoder('windows-1252')` sobre arrayBuffer) y quedarse con la versión con menos reemplazos. **Tests:** T-86 con bytes Latin-1 simulados.

---

## 5. CRITERIOS DE ACEPTACIÓN GLOBALES (verificación final, obligatoria)

1. `npm test` → **≥ 86 OK / 0 fallidas** (67 actuales + nuevos).
2. `node -e "…parse del <script>…"` sin errores de sintaxis (el harness ya lo hace implícitamente).
3. Smoke E2E en Node (patrón ya usado en el proyecto): texto → `cleanText` → `segment` → respuestas simuladas → `parseConsolidation` → `buildDocx` → `buildPackageZip`; validar ambos ZIP con `python3 -m zipfile -t` incluyendo el DOCX anidado (invariante C-01).
4. Auditoría manual de sinks: `grep -n 'innerHTML' index.html` — cada interpolación de datos no constantes pasa por `xmlEsc`/helper seguro.
5. Modo sensible ON: recorrer pasos 6, 7, 9, 10 y verificar que ningún botón de prompt está activo y que localStorage queda vacío.
6. Abrir `index.html` por `file://` sin red: pasos 1→10 completos con un `.txt` (sin librerías CDN).
7. `git push -u origin claude/realizar-pq01qv` al finalizar cada bloque de prioridad como mínimo.

---

## 6. NOTAS DE DISEÑO PARA LA IA EJECUTORA

- Antes de editar, **leer la función completa** en su estado actual; los números de línea de este plan se desplazan con cada tarea.
- No introducir abstracciones nuevas (clases, event-bus, state manager): el estilo del proyecto es funciones planas + `P` global. Imitarlo.
- Helpers nuevos que necesiten test → exportarlos en el bloque `Object.assign(globalThis,{...})` (R-10) y mantener el orden alfabético-temático existente.
- Cada commit: una tarea, mensaje `fix:`/`feat:`/`chore:` en español, cuerpo con los IDs de hallazgo (p. ej. "Corrige H-01, H-02").
- Si una aserción existente entra en conflicto con un cambio requerido (caso conocido: umbral 4 % de `validateResponse` en TAREA 7), actualizar el test citando este plan en el mensaje de commit, nunca borrarlo.
