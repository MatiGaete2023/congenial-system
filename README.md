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
   4. **Prompts por bloque** — copia un prompt optimizado para cada bloque.
   5. **Pegar respuestas** — pegue la respuesta de Claude/ChatGPT por bloque.
   6. **Consolidación** — copia un prompt que pide todos los productos en
      formato estructurado; pegue la respuesta consolidada.
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

La exportación a **Markdown y DOCX** se genera con código propio (un escritor
ZIP/OOXML incluido), sin librerías externas.

## Funcionamiento sin conexión (offline total)

TXT/Markdown, segmentación, prompts, consolidación, productos y exportación
funcionan sin red. La extracción de PDF/DOCX y el OCR usan tres librerías que,
por defecto, se cargan bajo demanda desde un CDN. Para uso 100% offline,
descargue y vendorice esas librerías:

```
vendor/
  pdf.min.js, pdf.worker.min.js   (pdf.js 3.x)
  tesseract.min.js + tessdata      (tesseract.js 5.x)
  mammoth.browser.min.js           (mammoth 1.x)
```

y reemplace las URLs del objeto `CDN` en `index.html` por rutas locales
(`vendor/...`). Tras ello, la aplicación no requiere conexión alguna.

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
