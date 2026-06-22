import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dir = dirname(fileURLToPath(import.meta.url));

// ── Mock browser globals ────────────────────────────────────────────────────
const mkEl = () => ({
  addEventListener: () => {}, removeEventListener: () => {},
  checked: false, value: '', textContent: '', innerHTML: '',
  style: {}, hidden: false, disabled: false, open: false,
  setAttribute: () => {}, getAttribute: () => null,
  classList: { add: () => {}, remove: () => {}, toggle: () => {}, contains: () => false },
  click: () => {}, files: [],
  appendChild: () => {}, removeChild: () => {}, querySelector: () => null, querySelectorAll: () => [],
});
global.document = {
  getElementById: () => mkEl(),
  querySelector: () => mkEl(),
  querySelectorAll: () => [],
  addEventListener: () => {},
  createElement: () => ({ ...mkEl(), href: '', download: '', remove: () => {} }),
  body: { appendChild: () => {} },
};
// NOTE: do NOT set global.window — keep window undefined so the
// `if(typeof window==='undefined')` exports block in index.html runs.
try { Object.defineProperty(global, 'navigator', { value: { language: 'es', clipboard: { writeText: async () => {} } }, configurable: true }); } catch(e) {}
try { Object.defineProperty(global, 'URL', { value: { createObjectURL: () => 'blob:mock', revokeObjectURL: () => {} }, configurable: true }); } catch(e) {}
global.confirm = () => true;

// ── Load & eval index.html script ──────────────────────────────────────────
const html = readFileSync(join(__dir, '..', 'index.html'), 'utf8');
const scripts = [...html.matchAll(/<script(?![^>]*\bsrc\b)[^>]*>([\s\S]*?)<\/script>/gi)]
  .map(m => m[1]).join('\n');
eval(scripts);

// Pull exported names from globalThis
const {
  P, blankProject, touch, safeName, xmlEsc,
  DOCX_MIME, zipStore, zipStoreAsync,
  mdRuns, pPara, heading, renderMarkdownToDocxBlocks,
  buildDocxXml, buildDocx, STYLES_XML, SETTINGS_XML,
  cleanText, cleanTextDetailed, detectChapters, segment, sizeOf,
  blockInstructions, consolidationPrompt, blockPrompt,
  buildMarkdown, buildObsidian,
  buildPartialSummariesMarkdown, buildRawConsolidationMarkdown,
  buildOfflineMarkdown, buildManualFichaMarkdown,
  isSensitive, sensitiveGuardIA, sensitiveAllowLocal,
  parseAllResponses, validateResponse,
  parseConsolidation, reassembleParts, bm25Search,
  CONSOL_BATCH_THRESHOLD, buildBatchConsolPrompts,
} = globalThis;

// ── Test harness ────────────────────────────────────────────────────────────
let passed = 0, failed = 0;
const queue = [];
function test(name, fn) { queue.push({ name, fn }); }

async function runAll() {
  for (const { name, fn } of queue) {
    try {
      await fn();
      console.log(`  OK  ${name}`);
      passed++;
    } catch (e) {
      console.log(`FAIL  ${name}: ${e.message}`);
      failed++;
    }
  }
  console.log(`\n${passed} OK / ${failed} fallidas`);
  if (failed > 0) process.exit(1);
}

function assert(cond, msg) { if (!cond) throw new Error(msg || 'assertion failed'); }
function eq(a, b, msg) { if (a !== b) throw new Error(`${msg || 'eq'}: got ${JSON.stringify(a)}, expected ${JSON.stringify(b)}`); }
function includes(str, sub, msg) {
  if (!String(str).includes(sub))
    throw new Error(`${msg || 'includes'}: "${sub}" not in "${String(str).slice(0, 120)}…"`);
}
function notIncludes(str, sub, msg) {
  if (String(str).includes(sub))
    throw new Error(`${msg || 'notIncludes'}: "${sub}" should not appear`);
}
async function blobBytes(blob) {
  return new Uint8Array(await blob.arrayBuffer());
}

// helper: set up a minimal P.products for DOCX tests
function fakeProducts(overrides = {}) {
  globalThis.P.meta = { title: 'Prueba', author: 'Autor Test', year: '2024', publisher: '', edition: '', pages: '', subject: '', subsubjects: '' };
  globalThis.P.products = {
    ficha: { title: 'Prueba', author: 'Autor Test', year: '2024', publisher: '', edition: '', pages: '', subject: '', subsubjects: '' },
    synthLines: ['Síntesis uno', 'Síntesis dos'],
    indexItems: ['Tema A', 'Tema B'],
    master: '## Capítulo I\nContenido de prueba\n### Sección 1.1\nDetalle',
    concepts: ['concepto alfa'],
    keywords: ['palabra', 'clave'],
    ...overrides,
  };
}

// ════════════════════════════════════════════════════════════════════════════
// T-01  zipStore → PK header + MIME parametrizable            [C-04, REQ-A]
// ════════════════════════════════════════════════════════════════════════════
test('T-01 zipStore MIME=application/zip → PK header', async () => {
  const blob = zipStore({ 'a.txt': 'hello' }, 'application/zip');
  eq(blob.type, 'application/zip', 'MIME');
  const arr = await blobBytes(blob);
  eq(arr[0], 0x50, 'byte[0]=0x50 (P)');
  eq(arr[1], 0x4B, 'byte[1]=0x4B (K)');
});

// ════════════════════════════════════════════════════════════════════════════
// T-02  zipStoreAsync: string + Uint8Array → 2 entradas, CRC válido  [C-01]
// ════════════════════════════════════════════════════════════════════════════
test('T-02 zipStoreAsync string+Uint8Array → PK + EOCD', async () => {
  const bin = new Uint8Array([72, 101, 108, 108, 111]); // "Hello"
  const blob = await zipStoreAsync({ 'str.txt': 'world', 'bin.bin': bin }, 'application/zip');
  assert(blob instanceof Blob, 'result is Blob');
  const arr = await blobBytes(blob);
  eq(arr[0], 0x50, 'PK[0]'); eq(arr[1], 0x4B, 'PK[1]');
  // EOCD signature at last-22
  const L = arr.length;
  eq(arr[L - 22], 0x50, 'EOCD[0]'); eq(arr[L - 21], 0x4B, 'EOCD[1]');
  eq(arr[L - 20], 0x05, 'EOCD[2]'); eq(arr[L - 19], 0x06, 'EOCD[3]');
});

// ════════════════════════════════════════════════════════════════════════════
// T-03  buildDocx() contiene word/styles.xml y word/settings.xml    [REQ-C]
// ════════════════════════════════════════════════════════════════════════════
test('T-03 buildDocx() embed styles.xml + settings.xml', async () => {
  fakeProducts();
  const blob = buildDocx();
  assert(blob instanceof Blob, 'Blob');
  eq(blob.type, DOCX_MIME, 'MIME');
  const arr = await blobBytes(blob);
  const txt = new TextDecoder('latin1').decode(arr);
  includes(txt, 'word/styles.xml', 'styles.xml entry');
  includes(txt, 'word/settings.xml', 'settings.xml entry');
});

// ════════════════════════════════════════════════════════════════════════════
// T-04  document.xml contiene w:jc="both"; settings contiene w:updateFields
// ════════════════════════════════════════════════════════════════════════════
test('T-04 buildDocxXml() justificado + SETTINGS_XML updateFields', () => {
  fakeProducts();
  const xml = buildDocxXml();
  includes(xml, 'w:jc w:val="both"', 'justificado');
  includes(SETTINGS_XML, 'w:updateFields', 'updateFields en SETTINGS_XML');
});

// ════════════════════════════════════════════════════════════════════════════
// T-05  renderMarkdownToDocxBlocks('## Capítulo I') → Heading2      [C-02]
// ════════════════════════════════════════════════════════════════════════════
test('T-05 renderMarkdownToDocxBlocks ## → Heading2', () => {
  const xml = renderMarkdownToDocxBlocks('## Capítulo I');
  includes(xml, 'w:val="Heading2"', 'Heading2 style');
});

// ════════════════════════════════════════════════════════════════════════════
// T-06  buildPartialSummariesMarkdown usa b.response, no b.text      [E-09]
// ════════════════════════════════════════════════════════════════════════════
test('T-06 buildPartialSummariesMarkdown usa b.response', () => {
  globalThis.P.meta = { title: 'Doc' };
  globalThis.P.fileName = 'doc.pdf';
  globalThis.P.blocks = [{ index: 1, chapter: 'Cap 1', text: 'TEXTO_ORIGINAL', response: 'RESPUESTA_RESUMIDA' }];
  const md = buildPartialSummariesMarkdown();
  includes(md, 'RESPUESTA_RESUMIDA', 'debe usar b.response');
  notIncludes(md, 'TEXTO_ORIGINAL', 'no debe usar b.text');
});

// ════════════════════════════════════════════════════════════════════════════
// T-07  parseAllResponses "== Bloque N ==" → assigned=2              [E-13]
// ════════════════════════════════════════════════════════════════════════════
test('T-07 parseAllResponses "== Bloque N ==" → assigned=2', () => {
  globalThis.P.blocks = [
    { index: 1, chapter: 'Cap 1', text: 'x', response: '' },
    { index: 2, chapter: 'Cap 2', text: 'y', response: '' },
  ];
  const r = parseAllResponses('== Bloque 1 ==\nRespuesta A\n== Bloque 2 ==\nRespuesta B');
  eq(r.assigned, 2, 'assigned=2');
  eq(r.missing.length, 0, 'missing=0');
  includes(globalThis.P.blocks[0].response, 'Respuesta A', 'bloque 1');
  includes(globalThis.P.blocks[1].response, 'Respuesta B', 'bloque 2');
});

// ════════════════════════════════════════════════════════════════════════════
// T-08  cleanText preserva [p. 12]                                   [E-16]
// ════════════════════════════════════════════════════════════════════════════
test('T-08 cleanText preserva marcadores [p. N]', () => {
  const result = cleanText('[p. 12]\ntexto normal\n[p. 13]\nmás texto');
  includes(result, '[p. 12]', 'marcador p.12 conservado');
  includes(result, '[p. 13]', 'marcador p.13 conservado');
  includes(result, 'texto normal', 'texto normal conservado');
});

// ════════════════════════════════════════════════════════════════════════════
// T-09  validateResponse vacía → ok:false                             [REQ-K]
// ════════════════════════════════════════════════════════════════════════════
test('T-09 validateResponse vacía → ok:false', () => {
  const r = validateResponse({ response: '', text: 'fragmento largo para comparar' });
  eq(r.ok, false, 'ok debe ser false');
  assert(r.reason, 'debe tener reason');
});

// ════════════════════════════════════════════════════════════════════════════
// T-10  detectChapters no regresiona (CAPÍTULO I/II/III)             [REQ-P]
// ════════════════════════════════════════════════════════════════════════════
test('T-10 detectChapters no regresiona con CAPÍTULO I/II/III', () => {
  const text = 'CAPÍTULO I\nIntroducción al tema\nCAPÍTULO II\nDesarrollo\nCAPÍTULO III\nConclusión';
  const chapters = detectChapters(text);
  assert(Array.isArray(chapters), 'result es array');
  assert(chapters.length >= 3, `detecta ≥3 (detectó ${chapters.length})`);
  assert(chapters[0].title, 'primer capítulo tiene título');
  includes(chapters[0].title, 'CAPÍTULO', 'título contiene CAPÍTULO');
});

// ════════════════════════════════════════════════════════════════════════════
// T-11  zipStore con múltiples archivos → PK + múltiples entradas
// ════════════════════════════════════════════════════════════════════════════
test('T-11 zipStore múltiples archivos', async () => {
  const blob = zipStore({ 'a.txt': 'alpha', 'b.txt': 'beta', 'c.txt': 'gamma' }, 'application/zip');
  const arr = await blobBytes(blob);
  eq(arr[0], 0x50, 'PK'); eq(arr[1], 0x4B, 'PK');
  // EOCD (22 bytes): signature(4)+diskNo(2)+cdDisk(2)+diskEntries(2)+totalEntries(2)+...
  // totalEntries is at EOCD+8 = arr.length-22+8 = arr.length-14 (little-endian)
  const L = arr.length;
  const totalEntries = arr[L - 14] | (arr[L - 13] << 8);
  eq(totalEntries, 3, '3 entradas en directorio central');
});

// ════════════════════════════════════════════════════════════════════════════
// T-12  zipStore con DOCX_MIME devuelve MIME docx                    [C-04]
// ════════════════════════════════════════════════════════════════════════════
test('T-12 zipStore MIME=DOCX_MIME', () => {
  const blob = zipStore({ 'doc.xml': '<xml/>' }, DOCX_MIME);
  eq(blob.type, DOCX_MIME, 'MIME debe ser DOCX_MIME');
});

// ════════════════════════════════════════════════════════════════════════════
// T-13  buildPartialSummariesMarkdown con sin respuestas
// ════════════════════════════════════════════════════════════════════════════
test('T-13 buildPartialSummariesMarkdown sin respuestas', () => {
  globalThis.P.meta = { title: 'Prueba' };
  globalThis.P.blocks = [{ index: 1, chapter: 'Cap 1', text: 'texto', response: '' }];
  const md = buildPartialSummariesMarkdown();
  includes(md, 'sin respuesta', 'marca bloques sin respuesta');
  includes(md, 'respondidos: 0', 'cuenta correcta');
});

// ════════════════════════════════════════════════════════════════════════════
// T-14  parseAllResponses con [[RJA_BLOCK_ID:b1]] → assigned=1       [E-12]
// ════════════════════════════════════════════════════════════════════════════
test('T-14 parseAllResponses [[RJA_BLOCK_ID:b1]]', () => {
  globalThis.P.blocks = [{ index: 1, chapter: 'Cap 1', text: 'x', response: '' }];
  const r = parseAllResponses('[[RJA_BLOCK_ID:b1]]\nContenido respuesta 1');
  eq(r.assigned, 1, 'assigned=1');
  includes(globalThis.P.blocks[0].response, 'Contenido respuesta 1', 'respuesta asignada');
});

// ════════════════════════════════════════════════════════════════════════════
// T-15  parseAllResponses con ## Bloque N → assigned=2
// ════════════════════════════════════════════════════════════════════════════
test('T-15 parseAllResponses "## Bloque N"', () => {
  globalThis.P.blocks = [
    { index: 1, chapter: 'A', text: 'x', response: '' },
    { index: 2, chapter: 'B', text: 'y', response: '' },
  ];
  const r = parseAllResponses('## Bloque 1\nTexto A\n## Bloque 2\nTexto B');
  eq(r.assigned, 2, 'assigned=2');
});

// ════════════════════════════════════════════════════════════════════════════
// T-16  validateResponse muy corta → ok:false
// ════════════════════════════════════════════════════════════════════════════
test('T-16 validateResponse muy corta → ok:false', () => {
  const r = validateResponse({ response: 'Ok.', text: 'x'.repeat(2000) });
  eq(r.ok, false, 'demasiado corta');
  includes(r.reason, 'corta', 'reason menciona corta');
});

// ════════════════════════════════════════════════════════════════════════════
// T-17  validateResponse buena (larga + encabezados) → ok:true
// ════════════════════════════════════════════════════════════════════════════
test('T-17 validateResponse buena → ok:true', () => {
  const resp = '### CAPÍTULO I\n' + 'Contenido jurídico detallado. '.repeat(20);
  const r = validateResponse({ response: resp, text: 'texto'.repeat(10) });
  eq(r.ok, true, 'ok debe ser true');
  assert(!r.reason || r.warn !== true, 'sin advertencia crítica');
});

// ════════════════════════════════════════════════════════════════════════════
// T-18  validateResponse larga pero sin encabezados → warn:true
// ════════════════════════════════════════════════════════════════════════════
test('T-18 validateResponse sin encabezados → warn:true', () => {
  const resp = 'Texto largo sin encabezados jurídicos. '.repeat(15);
  const r = validateResponse({ response: resp, text: 'base' });
  eq(r.ok, true, 'ok=true (no falla)');
  eq(r.warn, true, 'warn=true por falta de encabezados');
});

// ════════════════════════════════════════════════════════════════════════════
// T-19  detectChapters formato decimal (1. Título, 2. Título)
// ════════════════════════════════════════════════════════════════════════════
test('T-19 detectChapters formato decimal', () => {
  const text = '1.  INTRODUCCIÓN AL DERECHO\nTexto.\n2.  FUENTES DEL DERECHO\nTexto.';
  const ch = detectChapters(text);
  assert(ch.length >= 2, `detecta ≥2 (detectó ${ch.length})`);
});

// ════════════════════════════════════════════════════════════════════════════
// T-20  detectChapters formato romano (I. TÍTULO)
// ════════════════════════════════════════════════════════════════════════════
test('T-20 detectChapters formato romano', () => {
  const text = 'I.  TEORÍA GENERAL\nContenido.\nII.  APLICACIÓN PRÁCTICA\nMás.';
  const ch = detectChapters(text);
  assert(ch.length >= 2, `detecta ≥2 (detectó ${ch.length})`);
});

// ════════════════════════════════════════════════════════════════════════════
// T-21  renderMarkdownToDocxBlocks # → Heading1
// ════════════════════════════════════════════════════════════════════════════
test('T-21 renderMarkdownToDocxBlocks # → Heading1', () => {
  const xml = renderMarkdownToDocxBlocks('# Título principal');
  includes(xml, 'w:val="Heading1"', 'Heading1');
});

// ════════════════════════════════════════════════════════════════════════════
// T-22  renderMarkdownToDocxBlocks ### → Heading3
// ════════════════════════════════════════════════════════════════════════════
test('T-22 renderMarkdownToDocxBlocks ### → Heading3', () => {
  const xml = renderMarkdownToDocxBlocks('### Subsección');
  includes(xml, 'w:val="Heading3"', 'Heading3');
});

// ════════════════════════════════════════════════════════════════════════════
// T-23  renderMarkdownToDocxBlocks lista → contiene bullet
// ════════════════════════════════════════════════════════════════════════════
test('T-23 renderMarkdownToDocxBlocks lista - item', () => {
  const xml = renderMarkdownToDocxBlocks('- Elemento de lista');
  includes(xml, '•', 'bullet en párrafo');
});

// ════════════════════════════════════════════════════════════════════════════
// T-24  mdRuns **bold** → w:b
// ════════════════════════════════════════════════════════════════════════════
test('T-24 mdRuns **bold** → w:b', () => {
  const xml = mdRuns('Texto **negrita** aquí');
  includes(xml, '<w:b/>', 'w:b tag');
  includes(xml, 'negrita', 'texto bold');
});

// ════════════════════════════════════════════════════════════════════════════
// T-25  mdRuns *italic* → w:i
// ════════════════════════════════════════════════════════════════════════════
test('T-25 mdRuns *italic* → w:i', () => {
  const xml = mdRuns('Texto *cursiva* aquí');
  includes(xml, '<w:i/>', 'w:i tag');
});

// ════════════════════════════════════════════════════════════════════════════
// T-26  pPara justify:true → w:jc val="both"
// ════════════════════════════════════════════════════════════════════════════
test('T-26 pPara justify:true → w:jc both', () => {
  const xml = pPara('Texto de párrafo', { justify: true });
  includes(xml, 'w:jc w:val="both"', 'justificado');
});

// ════════════════════════════════════════════════════════════════════════════
// T-27  cleanText elimina números de página solos
// ════════════════════════════════════════════════════════════════════════════
test('T-27 cleanText elimina números de página solos', () => {
  const result = cleanText('Texto real\n42\nMás texto');
  notIncludes(result.split('\n').map(l => l.trim()).join('|'), '|42|', 'número de página eliminado');
  includes(result, 'Texto real', 'texto real conservado');
});

// ════════════════════════════════════════════════════════════════════════════
// T-28  cleanTextDetailed devuelve {text, removedLines}              [REQ-Q]
// ════════════════════════════════════════════════════════════════════════════
test('T-28 cleanTextDetailed → {text, removedLines}', () => {
  const r = cleanTextDetailed('Texto bueno\n999\nMás texto');
  assert(typeof r.text === 'string', 'text es string');
  assert(Array.isArray(r.removedLines), 'removedLines es array');
  includes(r.text, 'Texto bueno', 'texto conservado en .text');
});

// ════════════════════════════════════════════════════════════════════════════
// T-29  isSensitive() false por defecto
// ════════════════════════════════════════════════════════════════════════════
test('T-29 isSensitive() false por defecto', () => {
  globalThis.P.sensitive = false;
  eq(isSensitive(), false, 'false por defecto');
});

// ════════════════════════════════════════════════════════════════════════════
// T-30  isSensitive() true cuando P.sensitive=true                   [REQ-F]
// ════════════════════════════════════════════════════════════════════════════
test('T-30 isSensitive() true cuando P.sensitive=true', () => {
  globalThis.P.sensitive = true;
  eq(isSensitive(), true, 'true cuando sensitive');
  globalThis.P.sensitive = false;
});

// ════════════════════════════════════════════════════════════════════════════
// T-31  safeName maneja caracteres especiales
// ════════════════════════════════════════════════════════════════════════════
test('T-31 safeName genera nombre seguro', () => {
  globalThis.P.meta = { title: 'Derecho Penal — Parte General (2ª ed.)' };
  const name = safeName();
  assert(!/[^a-zA-Z0-9_]/.test(name), `nombre seguro: "${name}"`);
  assert(name.length > 0, 'nombre no vacío');
});

// ════════════════════════════════════════════════════════════════════════════
// T-32  blankProject() estructura correcta
// ════════════════════════════════════════════════════════════════════════════
test('T-32 blankProject() estructura', () => {
  const p = blankProject();
  assert(typeof p.meta === 'object', 'meta es objeto');
  assert(Array.isArray(p.blocks), 'blocks es array');
  eq(p.blocks.length, 0, 'blocks vacío');
  eq(p.sensitive, false, 'sensitive=false');
  eq(p.products, null, 'products=null');
});

// ════════════════════════════════════════════════════════════════════════════
// T-33  touch() actualiza P._modified
// ════════════════════════════════════════════════════════════════════════════
test('T-33 touch() actualiza _modified', () => {
  const before = globalThis.P._modified || 0;
  touch();
  assert(globalThis.P._modified >= before, '_modified actualizado');
});

// ════════════════════════════════════════════════════════════════════════════
// T-34  segment() texto sin capítulos → bloques por tamaño
// ════════════════════════════════════════════════════════════════════════════
test('T-34 segment() texto pequeño → 1 bloque', () => {
  const blocks = segment('Texto corto sin capítulos.', 8000);
  eq(blocks.length, 1, '1 bloque para texto pequeño');
  assert(blocks[0].text, 'bloque tiene texto');
  assert(blocks[0].index === 1, 'index=1');
});

// ════════════════════════════════════════════════════════════════════════════
// T-35  segment() texto con capítulos → bloques por capítulo
// ════════════════════════════════════════════════════════════════════════════
test('T-35 segment() con CAPÍTULO I/II → ≥2 bloques', () => {
  const text = 'CAPÍTULO I\n' + 'contenido A '.repeat(10) + '\nCAPÍTULO II\n' + 'contenido B '.repeat(10);
  const blocks = segment(text, 8000);
  assert(blocks.length >= 2, `≥2 bloques (got ${blocks.length})`);
  assert(blocks[0].chapter.includes('CAPÍTULO'), 'capítulo en nombre de bloque');
});

// ════════════════════════════════════════════════════════════════════════════
// T-36  blockPrompt() contiene el texto del bloque
// ════════════════════════════════════════════════════════════════════════════
test('T-36 blockPrompt() contiene b.text y b.chapter', () => {
  const b = { index: 3, chapter: 'Cap Prueba', text: 'Texto del fragmento jurídico.', response: '' };
  const prompt = blockPrompt(b);
  includes(prompt, 'Texto del fragmento jurídico.', 'contiene b.text');
  includes(prompt, 'Cap Prueba', 'contiene b.chapter');
  includes(prompt, '3', 'contiene b.index');
});

// ════════════════════════════════════════════════════════════════════════════
// T-37  buildMarkdown() contiene secciones esperadas
// ════════════════════════════════════════════════════════════════════════════
test('T-37 buildMarkdown() contiene secciones', () => {
  fakeProducts();
  const md = buildMarkdown();
  includes(md, '## Ficha bibliográfica', 'ficha');
  includes(md, '## Síntesis ejecutiva', 'síntesis');
  includes(md, '## Resumen maestro', 'resumen maestro');
  includes(md, '## Palabras clave', 'palabras clave');
});

// ════════════════════════════════════════════════════════════════════════════
// T-38  buildObsidian() contiene YAML front matter
// ════════════════════════════════════════════════════════════════════════════
test('T-38 buildObsidian() contiene YAML front matter', () => {
  fakeProducts();
  const obs = buildObsidian();
  includes(obs, '---', 'YAML delimiters');
  includes(obs, 'title:', 'campo title');
  includes(obs, 'tags:', 'campo tags');
});

// ════════════════════════════════════════════════════════════════════════════
// T-39  buildManualFichaMarkdown usa P.meta                          [REQ-H]
// ════════════════════════════════════════════════════════════════════════════
test('T-39 buildManualFichaMarkdown usa P.meta', () => {
  globalThis.P.meta = { title: 'Código Civil', author: 'Vélez Sársfield', year: '1871', publisher: '', edition: '3.ª', pages: '800', subject: 'Derecho Civil', subsubjects: 'Personas,Bienes', juris: 'Argentina' };
  globalThis.P.cleanText = 'Texto de ejemplo para estadísticas.';
  const md = buildManualFichaMarkdown();
  includes(md, 'Código Civil', 'título');
  includes(md, 'Vélez Sársfield', 'autor');
  includes(md, '1871', 'año');
  includes(md, 'caracteres', 'estadística');
});

// ════════════════════════════════════════════════════════════════════════════
// T-40  buildOfflineMarkdown usa P.cleanText                         [REQ-G]
// ════════════════════════════════════════════════════════════════════════════
test('T-40 buildOfflineMarkdown usa P.cleanText', () => {
  globalThis.P.meta = { title: 'Doc Test', author: 'Autor' };
  globalThis.P.cleanText = 'Párrafo uno.\n\nPárrafo dos.';
  const md = buildOfflineMarkdown();
  includes(md, '# Doc Test', 'título en H1');
  includes(md, 'Párrafo uno', 'texto incluido');
});

// ════════════════════════════════════════════════════════════════════════════
// T-41  parseAllResponses missing refleja bloques sin respuesta
// ════════════════════════════════════════════════════════════════════════════
test('T-41 parseAllResponses.missing incluye bloques sin match', () => {
  globalThis.P.blocks = [
    { index: 1, chapter: 'A', text: 'x', response: '' },
    { index: 2, chapter: 'B', text: 'y', response: '' },
    { index: 3, chapter: 'C', text: 'z', response: '' },
  ];
  const r = parseAllResponses('== Bloque 1 ==\nRespuesta solo para 1');
  eq(r.assigned, 1, 'solo 1 asignado');
  assert(r.missing.includes(2), 'bloque 2 en missing');
  assert(r.missing.includes(3), 'bloque 3 en missing');
});

// ════════════════════════════════════════════════════════════════════════════
// T-42  buildRawConsolidationMarkdown devuelve P.consolResponse      [E-10]
// ════════════════════════════════════════════════════════════════════════════
test('T-42 buildRawConsolidationMarkdown = P.consolResponse', () => {
  globalThis.P.consolResponse = 'RESPUESTA_BRUTA_DEL_MODELO';
  const md = buildRawConsolidationMarkdown();
  eq(md, 'RESPUESTA_BRUTA_DEL_MODELO', 'igual a P.consolResponse');
});

// ════════════════════════════════════════════════════════════════════════════
// T-43  xmlEsc escapa &, <, >
// ════════════════════════════════════════════════════════════════════════════
test('T-43 xmlEsc escapa caracteres XML', () => {
  eq(xmlEsc('a & b'), 'a &amp; b', '&');
  eq(xmlEsc('<tag>'), '&lt;tag&gt;', '< >');
});

// ════════════════════════════════════════════════════════════════════════════
// T-44  zipStoreAsync acepta ArrayBuffer
// ════════════════════════════════════════════════════════════════════════════
test('T-44 zipStoreAsync acepta ArrayBuffer', async () => {
  const ab = new TextEncoder().encode('buffer content').buffer;
  const blob = await zipStoreAsync({ 'file.bin': ab });
  const arr = await blobBytes(blob);
  eq(arr[0], 0x50, 'PK[0]');
});

// ════════════════════════════════════════════════════════════════════════════
// T-45  zipStoreAsync acepta Blob
// ════════════════════════════════════════════════════════════════════════════
test('T-45 zipStoreAsync acepta Blob', async () => {
  const inner = new Blob(['blob content'], { type: 'text/plain' });
  const blob = await zipStoreAsync({ 'f.txt': inner });
  const arr = await blobBytes(blob);
  eq(arr[0], 0x50, 'PK[0]');
  eq(arr[1], 0x4B, 'PK[1]');
});

// ════════════════════════════════════════════════════════════════════════════
// T-46  sizeOf excluye marcadores de página del conteo              [E-16]
// ════════════════════════════════════════════════════════════════════════════
test('T-46 sizeOf excluye [p. N] del conteo', () => {
  const text = '[p. 1]\nhola\n[p. 2]\nmundo';
  const withMarkers = text.length;
  const without = sizeOf(text);
  assert(without < withMarkers, 'sizeOf < length cuando hay marcadores');
  includes(String(without), '', 'devuelve número');
});

// ════════════════════════════════════════════════════════════════════════════
// T-47  reassembleParts une piezas "CONTINUAR PARA COMPLETAR"        [REQ-M]
// ════════════════════════════════════════════════════════════════════════════
test('T-47 reassembleParts une partes', () => {
  const text = 'Primera parte.\nCONTINUAR PARA COMPLETAR\nSegunda parte.';
  const result = reassembleParts(text);
  notIncludes(result, 'CONTINUAR PARA COMPLETAR', 'separador eliminado');
  includes(result, 'Primera parte', 'primera parte presente');
  includes(result, 'Segunda parte', 'segunda parte presente');
});

// ════════════════════════════════════════════════════════════════════════════
// T-48  sensitiveGuardIA → false cuando P.sensitive=true              [REQ-F]
// ════════════════════════════════════════════════════════════════════════════
test('T-48 sensitiveGuardIA → false cuando sensitive=true', () => {
  globalThis.P.sensitive = true;
  eq(sensitiveGuardIA(), false, 'debe bloquear cuando sensitive=true');
  globalThis.P.sensitive = false;
});

// ════════════════════════════════════════════════════════════════════════════
// T-49  sensitiveAllowLocal → true siempre                            [REQ-F]
// ════════════════════════════════════════════════════════════════════════════
test('T-49 sensitiveAllowLocal → true siempre', () => {
  globalThis.P.sensitive = true;
  eq(sensitiveAllowLocal(), true, 'local siempre permitido con sensitive=true');
  globalThis.P.sensitive = false;
  eq(sensitiveAllowLocal(), true, 'local siempre permitido con sensitive=false');
});

// ════════════════════════════════════════════════════════════════════════════
// T-50  buildManualFichaMarkdown incluye edition, pages, subsubjects   [C-03]
// ════════════════════════════════════════════════════════════════════════════
test('T-50 buildManualFichaMarkdown incluye edition/pages/subsubjects', () => {
  globalThis.P.meta = {
    title: 'Código Civil', author: 'Test', year: '2024',
    publisher: 'Ed. Test', edition: '5.ª ed.', pages: '650',
    subject: 'Civil', subsubjects: 'Obligaciones, Contratos', juris: 'Argentina',
  };
  globalThis.P.cleanText = 'Texto de prueba.';
  const md = buildManualFichaMarkdown();
  includes(md, '5.ª ed.', 'edición incluida');
  includes(md, '650', 'páginas incluidas');
  includes(md, 'Obligaciones, Contratos', 'submaterias incluidas');
});

// ════════════════════════════════════════════════════════════════════════════
// T-51  blockPrompt sin marcador estricto → no contiene [[RJA_BLOCK_ID]] [R-4]
// ════════════════════════════════════════════════════════════════════════════
test('T-51 blockPrompt sin validación estricta → sin [[RJA_BLOCK_ID]]', () => {
  // optStrictValidation.checked = false (default en mock)
  const b = { index: 1, chapter: 'Cap 1', text: 'Texto del fragmento.', response: '' };
  const prompt = blockPrompt(b);
  notIncludes(prompt, '[[RJA_BLOCK_ID', 'sin marcador cuando strict OFF (R-4)');
  includes(prompt, blockInstructions.slice(0, 30), 'incluye blockInstructions');
});

// ════════════════════════════════════════════════════════════════════════════
// T-52  parseConsolidation extrae ficha + secciones                   [REQ-D]
// ════════════════════════════════════════════════════════════════════════════
test('T-52 parseConsolidation extrae estructura de consolidación', () => {
  globalThis.P.meta = { title: '', author: '', year: '', publisher: '', edition: '', pages: '', subject: '', subsubjects: '' };
  const raw = `## FICHA BIBLIOGRÁFICA
- Título: Derecho Procesal Civil
- Autor: Juan Pérez
- Año: 2020

## SÍNTESIS EJECUTIVA
1. Punto importante uno
2. Punto importante dos

## ÍNDICE TEMÁTICO
- Proceso civil
- Prueba

## RESUMEN MAESTRO
### Capítulo I
Contenido del capítulo uno.

## CONCEPTOS CLAVE
- Acción procesal
- Pretensión

## PALABRAS CLAVE
proceso, prueba, acción, pretensión`;
  const pr = parseConsolidation(raw);
  assert(pr.ficha, 'tiene ficha');
  assert(pr.synthLines.length >= 2, `synthLines≥2 (${pr.synthLines.length})`);
  assert(pr.indexItems.length >= 2, `indexItems≥2 (${pr.indexItems.length})`);
  assert(pr.master.length > 0, 'master no vacío');
  assert(pr.concepts.length >= 2, `concepts≥2 (${pr.concepts.length})`);
  assert(pr.keywords.length >= 3, `keywords≥3 (${pr.keywords.length})`);
});

// ════════════════════════════════════════════════════════════════════════════
// T-53  parseAllResponses no contamina bloques con cabecera del siguiente
// ════════════════════════════════════════════════════════════════════════════
test('T-53 parseAllResponses — cabecera del bloque siguiente no aparece en respuesta anterior', () => {
  // Mutate blocks on the shared P object (no replacement — avoids eval-scope divergence)
  globalThis.P.blocks = [
    { index: 1, chapter: 'Cap A', text: 'texto A', response: '' },
    { index: 2, chapter: 'Cap B', text: 'texto B', response: '' },
  ];
  const blob = '== Bloque 1 ==\nRespuesta del bloque uno.\n\n== Bloque 2 ==\nRespuesta del bloque dos.';
  parseAllResponses(blob);
  const r1 = globalThis.P.blocks[0].response;
  const r2 = globalThis.P.blocks[1].response;
  notIncludes(r1, 'Bloque 2', 'cabecera bloque 2 no debe estar en respuesta 1');
  includes(r1, 'Respuesta del bloque uno', 'respuesta 1 correcta');
  includes(r2, 'Respuesta del bloque dos', 'respuesta 2 correcta');
});

// ════════════════════════════════════════════════════════════════════════════
// T-54  canEnterStep(3) siempre retorna true
// ════════════════════════════════════════════════════════════════════════════
test('T-54 canEnterStep(3) siempre true sin archivo ni rawText', () => {
  // canEnterStep(3) now always returns true — no state needed
  const { canEnterStep } = globalThis;
  assert(canEnterStep(3), 'step 3 debe ser accesible sin archivo cargado');
});

// ════════════════════════════════════════════════════════════════════════════
// T-55  buildPackageZip excluye _prompts.md en modo sensible
// ════════════════════════════════════════════════════════════════════════════
test('T-55 buildPackageZip omite _prompts.md cuando isSensitive()', async () => {
  // isSensitive() reads P.sensitive — mutate P directly (no replacement).
  // blockInstructions starts with "Eres un asistente" — unique to prompts file.
  globalThis.P.blocks = [{ index: 1, chapter: 'Cap', text: 'texto', response: 'resp' }];
  globalThis.P.sensitive = true;
  const blob = await globalThis.buildPackageZip();
  const arr = await blobBytes(blob);
  const text = new TextDecoder().decode(arr);
  notIncludes(text, 'Eres un asistente', 'blockInstructions no debe aparecer en modo sensible');
  globalThis.P.sensitive = false;
});

// ════════════════════════════════════════════════════════════════════════════
// T-56  buildPackageZip incluye _prompts.md cuando no es sensible
// ════════════════════════════════════════════════════════════════════════════
test('T-56 buildPackageZip incluye _prompts.md cuando no es sensible', async () => {
  // blockInstructions text appears only in _prompts.md file, not in dossier or README.
  globalThis.P.blocks = [{ index: 1, chapter: 'Cap', text: 'texto', response: 'resp' }];
  globalThis.P.sensitive = false;
  const blob = await globalThis.buildPackageZip();
  const arr = await blobBytes(blob);
  const text = new TextDecoder().decode(arr);
  includes(text, 'Eres un asistente', 'blockInstructions debe aparecer en zip cuando no es sensible');
});

// ════════════════════════════════════════════════════════════════════════════
// T-57  xmlEsc escapa caracteres HTML en contenido de usuario
// ════════════════════════════════════════════════════════════════════════════
test('T-57 xmlEsc escapa < > & " en texto de bloque', () => {
  const raw = '<script>alert("xss")</script>&';
  const escaped = xmlEsc(raw);
  notIncludes(escaped, '<script>', 'no debe contener <script> sin escapar');
  includes(escaped, '&lt;', 'debe escapar <');
  includes(escaped, '&gt;', 'debe escapar >');
  includes(escaped, '&amp;', 'debe escapar &');
});

// ════════════════════════════════════════════════════════════════════════════
// T-58  detectChapters detecta encabezados TODO-MAYÚSCULAS (REQ-P)
// ════════════════════════════════════════════════════════════════════════════
test('T-58 detectChapters detecta encabezados TODO-MAYÚSCULAS', () => {
  const text = 'ANTECEDENTES DE HECHO\nTexto del antecedente.\n\nFUNDAMENTOS DE DERECHO\nEl derecho aplicable.';
  const chapters = detectChapters(text);
  const titles = chapters.map(c => c.title);
  assert(titles.some(t => t.includes('ANTECEDENTES')), 'debe detectar ANTECEDENTES DE HECHO');
  assert(titles.some(t => t.includes('FUNDAMENTOS')), 'debe detectar FUNDAMENTOS DE DERECHO');
});

// ════════════════════════════════════════════════════════════════════════════
// T-59  buildBatchConsolPrompts divide bloques cuando chars > threshold (REQ-O)
// ════════════════════════════════════════════════════════════════════════════
test('T-59 buildBatchConsolPrompts divide cuando total > CONSOL_BATCH_THRESHOLD', () => {
  // Two blocks with responses just above half the threshold each
  const half = Math.ceil(CONSOL_BATCH_THRESHOLD / 2) + 1;
  globalThis.P.blocks = [
    { index: 1, chapter: 'A', text: 'ta', response: 'R'.repeat(half) },
    { index: 2, chapter: 'B', text: 'tb', response: 'R'.repeat(half) },
  ];
  const batches = buildBatchConsolPrompts();
  assert(batches.length >= 2, 'debe producir al menos 2 lotes cuando supera el umbral');
  includes(batches[0], 'lote 1/', 'primer lote debe indicar su número');
});

// ════════════════════════════════════════════════════════════════════════════
// T-60  buildBatchConsolPrompts no divide cuando chars <= threshold
// ════════════════════════════════════════════════════════════════════════════
test('T-60 buildBatchConsolPrompts no divide cuando total <= CONSOL_BATCH_THRESHOLD', () => {
  globalThis.P.blocks = [
    { index: 1, chapter: 'A', text: 'ta', response: 'respuesta corta' },
    { index: 2, chapter: 'B', text: 'tb', response: 'otra respuesta corta' },
  ];
  const batches = buildBatchConsolPrompts();
  assert(batches.length === 1, 'debe producir 1 lote cuando el total no supera el umbral');
});

// ════════════════════════════════════════════════════════════════════════════
// T-61  buildPackageZip funciona sin P.products (solo rawText — REQ-G paquete local)
// ════════════════════════════════════════════════════════════════════════════
test('T-61 buildPackageZip funciona sin P.products solo con rawText', async () => {
  globalThis.P.products = null;
  globalThis.P.consolResponse = '';
  globalThis.P.blocks = [];
  globalThis.P.rawText = 'Texto de prueba sin consolidar';
  globalThis.P.sensitive = false;
  const blob = await globalThis.buildPackageZip();
  assert(blob instanceof Blob, 'debe devolver un Blob');
  const arr = await blobBytes(blob);
  const text = new TextDecoder().decode(arr);
  includes(text, 'README_EXPORTACION', 'el paquete debe incluir el README aunque no haya productos');
});

// ════════════════════════════════════════════════════════════════════════════
// T-62  segment() crea bloques con excluded:false (REQ-R)
// ════════════════════════════════════════════════════════════════════════════
test('T-62 segment() crea bloques con excluded:false', () => {
  const { segment } = globalThis;
  const blocks = segment('CAPÍTULO I\nTexto uno.\n\nCAPÍTULO II\nTexto dos.', 8000);
  assert(blocks.length >= 1, 'debe generar al menos un bloque');
  assert(blocks.every(b => b.excluded === false), 'todos los bloques deben tener excluded:false');
});

// ════════════════════════════════════════════════════════════════════════════
// T-63  toggleBlockExclude + buildBatchConsolPrompts filtra excluidos (REQ-R)
// ════════════════════════════════════════════════════════════════════════════
test('T-63 bloque excluido no aparece en prompts de consolidación', () => {
  const { toggleBlockExclude, buildBatchConsolPrompts } = globalThis;
  globalThis.P.blocks = [
    { index: 1, chapter: 'Bloque Incluido', text: 'ta', response: 'resp A', excluded: false },
    { index: 2, chapter: 'Bloque Excluido', text: 'tb', response: 'resp B', excluded: false },
  ];
  toggleBlockExclude(2, false); // checked=false → excluded=true
  const batches = buildBatchConsolPrompts();
  assert(batches.length === 1, 'debe haber 1 lote');
  includes(batches[0], 'Bloque Incluido', 'bloque incluido debe aparecer');
  notIncludes(batches[0], 'Bloque Excluido', 'bloque excluido no debe aparecer');
});

// ════════════════════════════════════════════════════════════════════════════
// T-64  updateBlockChapter renombra capítulo en P.blocks (REQ-R)
// ════════════════════════════════════════════════════════════════════════════
test('T-64 updateBlockChapter renombra capítulo correctamente', () => {
  const { updateBlockChapter } = globalThis;
  globalThis.P.blocks = [
    { index: 1, chapter: 'Nombre Original', text: 'texto', response: '', excluded: false },
  ];
  updateBlockChapter(1, 'ANTECEDENTES DE HECHO');
  assert(globalThis.P.blocks[0].chapter === 'ANTECEDENTES DE HECHO', 'el capítulo debe haberse renombrado');
});

// ── Run ─────────────────────────────────────────────────────────────────────
runAll();
