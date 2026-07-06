# Resumidor Jurídico Asistido (RJA)

Orquestador documental **100% local** para resumir documentos jurídicos
extensos (libros de 70 a 500 páginas) con ayuda de **Claude** y **ChatGPT**
usando sus interfaces web — **sin APIs de pago, sin nube, sin telemetría**.

La aplicación es un único archivo HTML (`index.html`). Todo el procesamiento
ocurre en el navegador del usuario; el documento nunca sale del equipo.

## Cómo usar

1. Abra `index.html` en un navegador moderno (Chrome, Edge, Firefox).
   - Opción servidor local (recomendado para OCR): `python3 -m http.server`
     y abra `http://localhost:8000`.
2. Siga el asistente de 8 pasos:
   1. **Cargar archivo** — PDF, DOCX, TXT o Markdown (arrastrar y soltar).
   2. **Extraer y limpiar** — extracción de texto, OCR automático si el PDF
      es imagen, limpieza de encabezados/pies y normalización.
   3. **Estructura y bloques** — detección de capítulos y segmentación
      automática (los capítulos largos se dividen por tamaño).
   4. **Prompts por bloque** — copia un prompt diseñado para respuestas
      **extensas, específicas y concretas** (artículos, plazos, requisitos,
      definiciones textuales y autores), no generales. El detalle predeterminado
      es **Exhaustivo** y pide usar toda la capacidad útil de salida mediante
      **artefacto/canvas**, sin topes fijos de líneas. Si el fragmento excede el
      tamaño del chat, use **Modo adjunto**: descarga el fragmento (`.txt`/`.md`,
      o todos en `.zip`) para adjuntarlo y pega solo el prompt.
   5. **Pegar respuestas** — pegue la respuesta de Claude/ChatGPT por bloque.
   6. **Consolidación** — copia un prompt que pide todos los productos en
      formato estructurado y exige **máxima extensión útil** para el dossier
      final, idealmente como **artefacto/canvas**, para que los parciales largos
      no se reduzcan a un resumen corto.
   7. **Productos finales** — se separan y validan automáticamente.
   8. **Exportar** — Markdown, DOCX, Nota Obsidian y respaldo `.json`.

El usuario solo interviene donde la especificación lo exige: seleccionar el
archivo, enviar los prompts a Claude/ChatGPT, pegar las respuestas y ejecutar
la consolidación. Todo lo demás es automático.

## Productos generados

- **Ficha bibliográfica** (título, autor, año, editorial, edición, páginas,
  materia principal, submaterias).
- **Síntesis ejecutiva** de exactamente 8 líneas.
- **Resumen maestro** integral por capítulos.
- **Índice temático** reconstruido desde el resumen maestro.
- **Conceptos clave** (20–40, sin duplicados).
- **Palabras clave** (30–80, para clasificación documental).
- **Nota Obsidian** con YAML + Markdown + tags, lista para usar.

Cada producto muestra una validación contra los requisitos de la
especificación (p. ej. "Síntesis ejecutiva: 8/8 líneas"). Los productos son
editables antes de exportar.

## Persistencia y reanudación

- Los proyectos se guardan automáticamente en **IndexedDB** del navegador:
  documento, texto extraído, bloques, respuestas parciales, consolidación y
  productos finales.
- Puede **cerrar la aplicación y continuar después** sin reprocesar los
  capítulos ya completados.
- El menú **Proyectos** permite abrir, eliminar e **importar/exportar** un
  proyecto como `.json` para respaldarlo o moverlo a otro equipo.
- **No** se guardan conversaciones, credenciales, cookies ni tokens.

## Formatos de entrada

| Formato | Soporte |
|---|---|
| TXT / Markdown | Nativo, sin dependencias |
| PDF con texto | `pdf.js` (extracción de capa de texto) |
| PDF imagen | `pdf.js` + OCR local con `tesseract.js` (es+en) |
| DOCX | `mammoth.js` |
| Audio / vídeo (MP3, WAV, M4A, OGG, MP4, WEBM) | Transcripción **Whisper local** (`transformers.js`, modelo `whisper-tiny`) |

La exportación a **Markdown y DOCX** se genera con código propio (un escritor
ZIP/OOXML incluido), sin librerías externas.

El audio/vídeo se decodifica en el navegador (Web Audio API) a 16 kHz mono y se
transcribe con Whisper localmente. El modelo se descarga una sola vez (la primera
transcripción) y queda cacheado; la transcripción resultante alimenta el mismo
flujo de segmentación, prompts y consolidación.

## Herramientas locales (evoluciones)

Además del flujo de 8 pasos, hay dos herramientas que operan **100% en local**:

- **🔎 Consultar (RAG local)**: búsqueda léxica **BM25** sobre el texto extraído
  (sin red ni APIs). Escriba una pregunta y el sistema recupera los pasajes más
  relevantes y genera un **prompt acotado** para pegar en Claude/ChatGPT que
  responde *solo* con esos fragmentos (reduce alucinaciones y ahorra contexto en
  libros de 500 páginas).
- **🕸 Grafo conceptual**: grafo de co-ocurrencia entre los conceptos clave según
  el resumen maestro, renderizado como **SVG** propio (sin librerías) y
  exportable.

El paso 4 incluye además **descarga de prompts agrupados en lotes** bajo un
presupuesto de caracteres, para pegar menos veces en obras muy extensas.

## Funcionamiento sin conexión (offline total)

TXT/Markdown, segmentación, prompts, consolidación, productos y exportación
funcionan sin red. Las librerías de PDF/DOCX/OCR se cargan **de forma perezosa
real**: sólo se descargan la primera vez que se usan (no al abrir la app), así
que abrir la herramienta para trabajar con TXT/MD no baja nada.

Para uso 100% offline o en contextos sensibles, descargue y vendorice esas
librerías en una carpeta `vendor/`:

```
vendor/
  pdf.min.js, pdf.worker.min.js   (pdf.js 3.x)
  tesseract.min.js + tessdata      (tesseract.js 5.x)
  mammoth.browser.min.js           (mammoth 1.x)
```

y active el modo local **sin editar código** definiendo la bandera antes de que
cargue el script, p. ej. añadiendo en `index.html`:

```html
<script>window.RJA_LOCAL_VENDOR = true;</script>
```

(o cambie `USE_LOCAL_VENDOR` a `true` en el script). Con ello, el objeto `CDN`
apunta a `vendor/...` y la aplicación no realiza ninguna petición de red.

El botón **⚙ Offline/SRI** (cabecera) automatiza el vendorizado: descarga las
4 librerías desde su propio equipo para que las coloque en `vendor/`, y **calcula
los hashes SRI** (SHA-384) de cada una, generando el snippet
`<script>window.RJA_SRI = { … }</script>` listo para pegar.

## Seguridad y privacidad

- Los documentos **nunca se suben** a ningún servidor: el procesamiento es
  local y el modelo lo opera el usuario manualmente.
- En modo CDN (por defecto) la app **descarga código remoto** (las 3 librerías)
  desde cdnjs/jsdelivr. No sube datos, pero ejecuta scripts de terceros. Para
  contextos jurídicos sensibles use el modo `vendor/` local descrito arriba.
- Las versiones del CDN están **fijadas** (pinning). En modo CDN se añade
  `crossorigin="anonymous"` y, si se han fijado hashes en `window.RJA_SRI`, se
  aplica **`integrity`/SRI** a cada librería (el navegador rechaza el recurso si
  el hash no coincide). Los hashes se calculan con el botón **⚙ Offline/SRI**;
  por defecto el mapa va vacío para no romper la carga con un hash incorrecto.
- La importación de proyectos `.json` se **valida y sanea** (`normalizeProject`)
  antes de cargarse, de modo que un archivo corrupto no rompe la app.
- No se guardan conversaciones, credenciales, cookies ni tokens.

## Robustez

- **Reanudación segura**: al reabrir un proyecto el botón de extracción queda
  deshabilitado hasta volver a seleccionar el archivo original (no se puede
  re-extraer sin el archivo en memoria).
- **OCR configurable y cancelable**: escala 1.5×/2×/2.5× y botón *Cancelar*;
  se libera la memoria de cada página tras procesarla.
- **Aviso de archivos grandes** (>50 MB) antes de procesar.
- **Parser de consolidación tolerante**: acepta encabezados con `##`, numerados
  (`1.`), en negrita o sin marcado, y campos de ficha vacíos o con marcadores
  como `(desconocido)`/`N/A`.
- **Navegación guiada**: no se puede saltar a un paso sin cumplir los previos.
- **Integridad SRI configurable** y vendorizado automático (botón ⚙ Offline/SRI).

## Pruebas

Funciones puras con cobertura de regresión (parser, limpieza, detección de
capítulos y escritor ZIP/DOCX con verificación de CRC):

```
npm test      # o: node tests/run.mjs
```

El desarrollo sigue el ciclo controlado descrito en [`AUTOLOOP.md`](AUTOLOOP.md)
(objetivo → cambio mínimo → prueba → corrección, máx. 3 iteraciones, registro).
Historial de versiones en [`CHANGELOG.md`](CHANGELOG.md); roadmap de auditoría
en [`PLAN_MAESTRO.md`](PLAN_MAESTRO.md). Licencia MIT ([`LICENSE`](LICENSE)).

En obras muy extensas, el paso 6 divide la consolidación automáticamente en
**etapas** (una consolidación parcial por grupo de bloques) más un prompt de
**fusión final**, para no exceder el límite de entrada del chat.

## Arquitectura

```
Usuario → Carga → Extracción/OCR → Limpieza → Detección estructural
       → Segmentación en bloques → Prompts → (Claude/ChatGPT, manual)
       → Respuestas parciales → Consolidación → Resumen maestro
       → Productos derivados → Exportación (MD/DOCX/Obsidian)
```

No se realizan llamadas a APIs externas para el procesamiento principal: el
modelo de lenguaje lo opera el usuario a través de la interfaz web del
proveedor.

## Restricciones respetadas

Prohibido y **no implementado**: dependencia obligatoria de APIs, servicios en
nube, envío automático de documentos, telemetría y almacenamiento remoto. El
sistema funciona completamente en local.

## Estado

MVP conforme a la *Especificación Técnica Mínima*. Evoluciones futuras
(procesamiento por lotes, grafos conceptuales, RAG local, Whisper, etc.)
quedan fuera de este alcance.
