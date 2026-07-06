/*
 * Pruebas de regresión para funciones puras de index.html (sin navegador).
 * Ejecuta con:  node tests/run.mjs
 *
 * No requiere dependencias ni red: extrae las funciones puras del HTML por
 * coincidencia de llaves y las evalúa en un sandbox (new Function), con stubs
 * mínimos. Cubre el parser de consolidación, limpieza, detección de capítulos
 * y el escritor ZIP/DOCX propio (estructura + CRC).
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const scriptMatch = html.match(/<script>\s*"use strict";([\s\S]*?)<\/script>/);
if (!scriptMatch) throw new Error('No se encontró el script principal de index.html');
const script = scriptMatch[1];

// --- extraer una función por nombre vía coincidencia de llaves ---
function grabFn(name){
  const i = script.indexOf('function ' + name + '(');
  if (i < 0) throw new Error('No se encontró función ' + name);
  let depth = 0, started = false, j = i;
  for (; j < script.length; j++){
    const c = script[j];
    if (c === '{'){ depth++; started = true; }
    else if (c === '}'){ depth--; if (started && depth === 0){ j++; break; } }
  }
  return script.slice(i, j);
}
function grabConst(re){ const m = script.match(re); if(!m) throw new Error('const no encontrada: '+re); return m[0]; }

const pieces = [
  grabConst(/const CHAP_RE=new RegExp\([\s\S]*?\);/),
  grabConst(/const KNOWN_SECTIONS=\[[\s\S]*?\];/),
  grabConst(/const STOPWORDS_ES=new Set\([\s\S]*?\);/),
  `const P={meta:{title:'Obra prueba',author:'Autora X',year:'2026',publisher:'Editorial',subject:'Derecho civil',juris:'Chile'},blocks:[{index:1,chapter:'Capítulo I',response:'Art. 2514: definición literal, plazo de cinco años, postura de Alessandri.'}]};`,
  grabFn('stripAccents'), grabFn('headerKey'), grabFn('splitSections'),
  grabFn('listItems'), grabFn('csvItems'), grabFn('dedupe'), grabFn('cleanVal'),
  grabFn('parseFicha'), grabFn('cleanText'), grabFn('detectChapters'),
  grabFn('rebuildIndex'), grabFn('zipStore'),
  grabFn('tokenize'), grabFn('splitPassages'), grabFn('bm25Search'),
  grabFn('groupIntoLotes'), grabFn('consolidationPlan'),
  grabFn('buildConceptGraph'), grabFn('graphToSvg'),
  grabFn('fragmentContent'), grabFn('consolidationPrompt'),
  grabFn('uid'), grabFn('blankProject'), grabFn('normalizeProject'),
];
const factory = new Function(pieces.join('\n') +
  '\nreturn {stripAccents,headerKey,splitSections,listItems,csvItems,dedupe,cleanVal,parseFicha,cleanText,detectChapters,rebuildIndex,zipStore,tokenize,splitPassages,bm25Search,groupIntoLotes,consolidationPlan,buildConceptGraph,graphToSvg,fragmentContent,consolidationPrompt,normalizeProject};');
const A = factory();

// --- mini framework ---
let pass = 0, fail = 0;
function ok(cond, msg){ if(cond){ pass++; } else { fail++; console.error('  ✗ ' + msg); } }
function eq(a, b, msg){ ok(JSON.stringify(a) === JSON.stringify(b), `${msg} — esperado ${JSON.stringify(b)}, obtenido ${JSON.stringify(a)}`); }

// --- 1. stripAccents ---
eq(A.stripAccents('Síntesis Ejecútiva ÑOÑO'), 'Sintesis Ejecutiva NONO', 'stripAccents');

// --- 2. headerKey tolera variantes ---
eq(A.headerKey('## FICHA BIBLIOGRÁFICA'), 'FICHA BIBLIOGRAFICA', 'headerKey ##');
eq(A.headerKey('### 1. Conceptos clave:'), 'CONCEPTOS CLAVE', 'headerKey numerado');
eq(A.headerKey('**Síntesis ejecutiva**'), 'SINTESIS EJECUTIVA', 'headerKey bold');
eq(A.headerKey('PALABRAS CLAVE'), 'PALABRAS CLAVE', 'headerKey plano');

// --- 3. splitSections con formato mixto ---
const consolidated = `Aquí va la respuesta.

## FICHA BIBLIOGRÁFICA
- Título: Manual de Derecho Procesal
- Autor: Juan Pérez
- Año:
- Editorial: (desconocida)
- Edición: 3ª
- Número de páginas: 320
- Materia principal: Derecho Procesal
- Submaterias: recursos, prueba

### 2. Síntesis ejecutiva
L1
L2

**Resumen maestro**
Texto del resumen maestro.

## ÍNDICE TEMÁTICO
- Capítulo I — Principios
- Capítulo II — Procedimiento

## Conceptos clave
- acción
- excepción
- Acción

## PALABRAS CLAVE
prueba, recurso, sentencia, Prueba`;
const S = A.splitSections(consolidated);
eq(Object.keys(S).sort(), ['CONCEPTOS CLAVE','FICHA BIBLIOGRAFICA','INDICE TEMATICO','PALABRAS CLAVE','RESUMEN MAESTRO','SINTESIS EJECUTIVA'], 'splitSections detecta 6 secciones');
ok(/Manual de Derecho Procesal/.test(S['FICHA BIBLIOGRAFICA']), 'sección ficha con contenido');
ok(/resumen maestro/.test(S['RESUMEN MAESTRO']), 'resumen maestro sin "##"');

// --- 4. parseFicha: vacíos y placeholders → '' ---
const f = A.parseFicha(S['FICHA BIBLIOGRAFICA']);
eq(f.title, 'Manual de Derecho Procesal', 'ficha título');
eq(f.year, '', 'ficha año vacío');
eq(f.publisher, '', 'ficha editorial placeholder (desconocida) → vacío');
eq(f.pages, '320', 'ficha páginas');

// --- 5. dedupe insensible a acentos/mayúsculas ---
eq(A.dedupe(A.listItems(S['CONCEPTOS CLAVE'])), ['acción','excepción'], 'dedupe conceptos');
eq(A.dedupe(A.csvItems(S['PALABRAS CLAVE'])), ['prueba','recurso','sentencia'], 'dedupe palabras clave');

// --- 6. detectChapters ---
const libro = 'Portada\n\nCapítulo I\nPrincipios generales\n\nCAPÍTULO II\nDel procedimiento\n\nTítulo III\nRecursos';
eq(A.detectChapters(libro).map(h=>h.title), ['Capítulo I','CAPÍTULO II','Título III'], 'detectChapters');

// --- 7. cleanText elimina encabezado recurrente y números de página sueltos ---
const dirty = Array.from({length:6}, (_,i)=>`ENCABEZADO REPETIDO\nContenido página ${i+1}\n${i+1}`).join('\n');
const clean = A.cleanText(dirty);
ok(!/ENCABEZADO REPETIDO/.test(clean), 'cleanText quita encabezado repetido');
ok(/Contenido página 3/.test(clean), 'cleanText conserva contenido');
ok(/jurídica/.test(A.cleanText('ju-\nrídica')) && /económico/.test(A.cleanText('eco-\nnómico')),
  'cleanText une palabras cortadas con guion ante acentos');

// --- 8. zipStore: estructura DOCX + CRC verificables ---
function crc32(buf){
  let c = ~0;
  for (let i=0;i<buf.length;i++){ c ^= buf[i];
    for (let k=0;k<8;k++) c = (c & 1) ? (0xEDB88320 ^ (c>>>1)) : (c>>>1); }
  return (~c) >>> 0;
}
const docxBlob = A.zipStore({
  '[Content_Types].xml': '<Types/>',
  '_rels/.rels': '<Relationships/>',
  'word/document.xml': '<w:document>contenido</w:document>',
});
const buf = Buffer.from(await docxBlob.arrayBuffer());
// localizar End Of Central Directory
const eocd = buf.lastIndexOf(Buffer.from([0x50,0x4b,0x05,0x06]));
ok(eocd > 0, 'EOCD presente');
const total = buf.readUInt16LE(eocd + 10);
eq(total, 3, 'zip tiene 3 entradas');
// recorrer cabeceras locales y verificar CRC de cada entrada
let p = 0, names = [], crcOk = true;
while (buf.readUInt32LE(p) === 0x04034b50){
  const crcStored = buf.readUInt32LE(p + 14);
  const size = buf.readUInt32LE(p + 18);
  const nameLen = buf.readUInt16LE(p + 26);
  const extraLen = buf.readUInt16LE(p + 28);
  const name = buf.slice(p + 30, p + 30 + nameLen).toString('utf8');
  const dataStart = p + 30 + nameLen + extraLen;
  const data = buf.slice(dataStart, dataStart + size);
  names.push(name);
  if (crc32(data) !== crcStored) crcOk = false;
  p = dataStart + size;
}
eq(names.sort(), ['[Content_Types].xml','_rels/.rels','word/document.xml'], 'nombres de entradas DOCX');
ok(crcOk, 'CRC de cada entrada coincide');

// --- 9. tokenize: minúsculas, sin acentos, sin stopwords, min 3 ---
eq(A.tokenize('El recurso de Casación, y la PRESCRIPCIÓN.'), ['recurso','casacion','prescripcion'], 'tokenize');

// --- 10. splitPassages respeta tamaño y párrafos ---
eq(A.splitPassages('aaaa\n\nbbbb\n\ncccc', 6).map(p=>p.text), ['aaaa','bbbb','cccc'], 'splitPassages');

// --- 11. bm25Search rankea el pasaje relevante primero ---
const PS = [
  {id:0,text:'La prescripción extingue las acciones por el transcurso del tiempo'},
  {id:1,text:'El recurso de casación procede contra sentencias definitivas'},
  {id:2,text:'La prueba documental se rige por reglas especiales'},
];
const hits = A.bm25Search(PS, 'prescripción de acciones', 3);
ok(hits.length >= 1 && hits[0].id === 0, 'bm25 prioriza el pasaje de prescripción');
eq(A.bm25Search(PS, '', 3), [], 'bm25 con query vacía → []');

// --- 12. groupIntoLotes agrupa bajo el presupuesto ---
const LB = [{index:1,text:'x'.repeat(10)},{index:2,text:'y'.repeat(10)},{index:3,text:'z'.repeat(5)}];
eq(A.groupIntoLotes(LB, 15).map(l=>l.map(b=>b.index)), [[1],[2,3]], 'groupIntoLotes');

// --- 13. buildConceptGraph: co-ocurrencia por párrafo ---
const G = A.buildConceptGraph(['prescripción','acción','recurso'],
  'La prescripción y la acción civil.\nEl recurso de casación.', 1);
eq(G.edges, [{a:0,b:1,w:1}], 'buildConceptGraph co-ocurrencia');
const G2 = A.buildConceptGraph(['acción','pago'], 'La transacción implica un pago.\nLa acción y el pago.', 1);
eq(G2.nodes[0].count, 1, 'buildConceptGraph exige frontera de palabra (acción ≠ transacción)');
ok(/^<svg/.test(A.graphToSvg(G)) && /prescripci/.test(A.graphToSvg(G)), 'graphToSvg renderiza nodos');

// --- 14. fragmentContent: cabecera txt/md + texto ---
eq(A.fragmentContent({index:3,chapter:'Cap I',text:'Hola'}, false), 'BLOQUE 3 — Cap I\n\nHola', 'fragmentContent txt');
eq(A.fragmentContent({index:3,chapter:'Cap I',text:'Hola'}, true), '# Bloque 3 — Cap I\n\nHola', 'fragmentContent md');

// --- 15. prompts: sin topes de líneas y modo exhaustivo por defecto ---
ok(/<option value="exhaustivo" selected>Exhaustivo<\/option>/.test(html), 'detalle exhaustivo por defecto');
ok(/usa toda la capacidad útil de salida/i.test(html) && /EXTENSIÓN MÁXIMA/.test(html), 'prompts piden máxima capacidad útil');
ok(!/(5[–-]8|15[–-]25|30[–-]40|Mínimo \d+)/.test(html), 'prompts sin mínimos/topes fijos de líneas');

// --- 16. consolidación: artefacto/canvas y máxima profundidad final ---
const CP = A.consolidationPrompt();
ok(/EXTENSIÓN MÁXIMA DE CONSOLIDACIÓN/.test(CP), 'consolidación tiene regla explícita de máxima extensión');
ok(/ARTEFACTO \(Claude\) o CANVAS \(ChatGPT\)/.test(CP), 'consolidación pide artefacto/canvas');
ok(/No conviertas respuestas parciales largas en un resumen corto/.test(CP), 'consolidación evita acortar parciales largos');
ok(/CONTINUAR PARA COMPLETAR/.test(CP), 'consolidación indica continuación si no cabe todo');

// --- 17. consolidationPlan: single vs jerárquico ---
const bigBlocks = Array.from({length:40},(_,i)=>({index:i+1,chapter:'C'+(i+1),text:'',response:'r'.repeat(3000)}));
const planH = A.consolidationPlan(bigBlocks, 30000);
eq(planH.mode, 'hierarchical', 'plan jerárquico cuando los parciales exceden el presupuesto');
eq(planH.groups.length, 4, 'plan jerárquico agrupa 40×3000 bajo 30000 en 4 etapas');
eq(planH.groups.map(g=>g.length), [10,10,10,10], 'etapas de 10 bloques');
const planS = A.consolidationPlan(bigBlocks.slice(0,5), 30000);
eq(planS.mode, 'single', 'plan single cuando los parciales caben');
eq(planS.groups.length, 1, 'single = 1 grupo');
// groupIntoLotes con medidor alternativo (lenOf)
eq(A.groupIntoLotes([{text:'x'.repeat(999),response:'ab'},{text:'',response:'cd'}], 3, b=>b.response.length)
  .map(l=>l.length), [1,1], 'groupIntoLotes respeta lenOf (mide response, no text)');

// --- 18. normalizeProject: solo claves del esquema, tipos corregidos ---
const NP = A.normalizeProject({fileName:'doc.pdf', junk:'basura', blocks:'no-array', step:'99', consolPartials:[1,'ok']});
ok(!('junk' in NP), 'normalizeProject descarta claves desconocidas');
eq(NP.fileName, 'doc.pdf', 'normalizeProject conserva claves válidas');
eq(NP.blocks, [], 'normalizeProject corrige blocks no-array');
eq(NP.step, 7, 'normalizeProject acota step al rango 0–7');
eq(NP.consolPartials, ['','ok'], 'normalizeProject sanea consolPartials a strings');

// --- resumen ---
console.log(`\n${fail === 0 ? '✓' : '✗'} Pruebas: ${pass} OK, ${fail} fallidas`);
process.exit(fail === 0 ? 0 : 1);
