# RJA — Resúmenes Jurídicos Asistidos v0.3.0

Herramienta de escritorio para resumir y estructurar documentos jurídicos extensos.
Funciona como un único archivo `index.html` sin instalación ni servidor.

---

## Modelo de funcionamiento — qué es local y qué no

| Operación | Dónde ocurre | Red requerida |
|---|---|---|
| Limpieza y segmentación de texto | Navegador (local) | No |
| Generación de ZIP, DOCX, Markdown | Navegador (local) | No |
| Búsqueda BM25, estadísticas, ficha | Navegador (local) | No |
| Exportación de proyecto (.json) | Navegador (local) | No |
| **Resúmenes de bloques** | **IA externa — Claude.ai / ChatGPT / otro** | **Sí (manual)** |
| **Consolidación** | **IA externa — Claude.ai / ChatGPT / otro** | **Sí (manual)** |
| Extracción de texto PDF (nativo) | PDF.js en navegador | CDN o archivo local |
| Extracción de texto DOCX | Mammoth.js en navegador | CDN o archivo local |
| OCR de imágenes | Tesseract.js *(experimental, offline parcial)* | CDN + tessdata ~30 MB |
| Transcripción de audio | No implementado *(experimental, offline parcial)* | N/A |

> **La IA de resúmenes NO es local.** Usted copia el prompt generado por RJA, lo pega en
> Claude.ai, ChatGPT u otro servicio web, obtiene la respuesta y la pega de vuelta.
> El texto de su documento viaja al servidor de ese servicio según sus propias políticas.
> Use el **modo Material Sensible** para documentos confidenciales.

---

## Apto / No apto para distintos contextos

### Apto para uso completamente sin red
- Extraer texto de PDF con texto nativo (si PDF.js está cacheado o cargado localmente)
- Limpiar, segmentar y analizar texto
- Exportar a ZIP, DOCX, Markdown, JSON, TXT
- Búsqueda BM25 local
- Ficha bibliográfica manual
- Modo Material Sensible (bloquea envío a IA)

### Requiere conexión a internet (primera carga o sin caché)
- Carga de PDF.js, Mammoth.js desde CDN
- OCR con Tesseract.js (descarga modelos ~30 MB por idioma)

### Requiere conexión y cuenta en servicio externo siempre
- Resúmenes de bloques (IA externa: Claude.ai, ChatGPT, etc.)
- Consolidación del dossier (IA externa)

### No implementado / experimental
- Transcripción de audio (Transformers.js / Whisper-tiny: pesos ~75 MB)
- OCR multilenguaje avanzado

---

## Instalación

Ninguna. Abra `index.html` en un navegador moderno (Chrome, Firefox, Edge, Safari).

Para funciones de extracción PDF/DOCX necesita cargar las librerías (ver "Librerías de terceros").

---

## Flujo de trabajo

```
1 Cargar    → 2 Metadatos → 3 Extraer → 4 Limpiar → 5 Segmentar
     ↓
6 Resumir (copiar prompts → IA externa → pegar respuestas)
     ↓
7 Consolidar (copiar prompt → IA externa → pegar respuesta)
     ↓
8 Productos → 9 Exportar (ZIP con DOCX, MD, Obsidian, JSON…)

⚙ Panel Local: accesible desde cualquier punto con texto extraído,
  sin necesidad de pasar por IA.
```

---

## Modo "Material Sensible"

Active el toggle **Material sensible** en el encabezado cuando trabaje con
documentos confidenciales. Con este modo activo:

**Quedan bloqueados** (ningún texto sale hacia IA externa):
- Copiar prompt de bloque
- Copiar prompt de consolidación
- Exportar prompts con texto

**Permanecen activos** (solo operaciones locales):
- Extracción, limpieza y segmentación
- Exportaciones ZIP, DOCX, Markdown, JSON
- Ficha manual, BM25, herramientas locales

---

## Librerías de terceros

Para extracción de texto la herramienta utiliza (opcionales, no incluidas):

| Librería | Función | Estado |
|---|---|---|
| PDF.js | Extracción de texto nativo de PDF | Estable |
| Mammoth.js | Extracción de texto de DOCX | Estable |
| Tesseract.js | OCR en imágenes y PDF escaneado | Experimental — offline parcial |
| Transformers.js + Whisper-tiny | Transcripción de audio | Experimental — offline parcial |

Cargue estas librerías desde CDN o desde archivos locales antes de usar extracción PDF/DOCX/OCR.

---

## Privacidad

- El texto de su documento **nunca se envía automáticamente** a ningún servidor.
- Al copiar un prompt y pegarlo en Claude.ai/ChatGPT, el fragmento de texto
  incluido viaja al servidor de ese servicio según sus propias políticas de privacidad.
- Use el modo **Material Sensible** para documentos con información confidencial.

---

## Desarrollo y tests

```bash
npm test   # → 61 OK / 0 fallidas
```

Los tests cubren: ZIP (CRC32, MIME, binario), DOCX (estilos, TOC, Markdown→Word),
limpieza de texto, detección de capítulos (decimal, romano, TODO-MAYÚSCULAS),
segmentación, pegado masivo, validación heurística de respuestas, modo sensible,
exportaciones, navegación de pasos, XSS-escape de contenido de usuario,
guard de prompts en modo sensible, consolidación por lotes y paquete local sin productos.

---

## Invariantes de diseño

- Sin APIs de pago. La IA se opera manualmente (copiar/pegar).
- Ejecución 100% local como archivo HTML. Sin instalación con privilegios.
- Los prompts sustantivos (`blockInstructions`, `consolidationPrompt`) no se modifican.
- Marcadores de página `[p. N]` y marcador de bloque `[[RJA_BLOCK_ID]]` son opt-in,
  desactivados por defecto. El comportamiento sin ellos es idéntico al original.
