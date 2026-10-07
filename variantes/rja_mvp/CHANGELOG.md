# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es/). Versionado semántico.

## [0.4.0] — 2026-07-06

Cierre de la auditoría descrita en `PLAN_MAESTRO.md` (tareas T1–T14).

### Corregido
- **XSS** por `innerHTML` con el nombre de archivo en carga y apertura de
  proyectos (explotable vía `.json` importado). *(T1, commit paralelo `4c80bb2`)*
- Cargar un archivo nuevo ahora **resetea consolidación y productos** del
  documento anterior, con confirmación si había trabajo hecho. *(T2)*
- **Confirmación antes de re-segmentar** cuando el nuevo corte descartaría
  respuestas ya pegadas. *(T3)*
- `loadScript` deduplica por **URL absoluta**: el modo `vendor/` ya no
  re-inyecta las librerías en cada uso. *(T4)*
- Las palabras cortadas con guion se unen también ante **acentos y ñ**. *(T6)*
- El grafo conceptual exige **frontera de palabra**: "acción" ya no co-ocurre
  dentro de "transacción". *(T7)*
- `normalizeProject` construye el proyecto **solo con claves del esquema**: un
  `.json` importado no puede inyectar campos ajenos. *(T9)*

### Añadido
- **Consolidación jerárquica**: cuando los resúmenes parciales exceden el
  presupuesto de un prompt (60.000 caracteres), el paso 6 divide la
  consolidación en etapas (prompt + respuesta por grupo) y genera un prompt de
  **fusión final**. Estado persistido y reanudable. *(T5)*
- **Smoke test DOM** en la suite: ejecuta el script completo con un arnés
  mínimo y falla ante ids inexistentes o errores de cableado. *(T10)*
- **Layout responsive** (<900 px: navegación horizontal, una columna),
  focos visibles (`:focus-visible`) y `aria-valuenow` en las barras de
  progreso. *(T11)*
- **Badges de progreso** en la navegación: nº de bloques y respuestas X/N. *(T12)*
- **Tema claro** automático (`prefers-color-scheme`); los colores fijos
  pasaron a variables CSS. *(T13)*
- `LICENSE` (MIT) y este `CHANGELOG.md`. *(T14)*

### Rendimiento
- Autosave: serialización única y **sin escrituras** si el contenido no cambió;
  debounce a 1 s. El corpus del RAG se **cachea** entre búsquedas. *(T8)*

## [0.3.0] — 2026-06-21

### Añadido
- Prompts por bloque con **reglas de especificidad obligatorias** (artículos,
  plazos, requisitos, definiciones textuales, autores) y secciones de citas.
- **Selector de nivel de detalle** (Breve / Estándar / Exhaustivo, por defecto
  Exhaustivo) y refuerzo de extensión máxima en prompts y consolidación.
- **Modo adjunto** para fragmentos grandes: descarga `.txt`/`.md`/`.zip` y
  prompt con nota de adjunto.
- Opción **artefacto/canvas** para respuestas largas.

## [0.2.0] — 2026-06-20

### Añadido
- **RAG local** (BM25) con prompt acotado; **grafo conceptual** SVG;
  **lotes** de prompts bajo presupuesto de caracteres.
- **Transcripción Whisper local** para audio/vídeo (`transformers.js`).
- **SRI** configurable y panel **⚙ Offline/SRI** (vendorizado + hashes SHA-384).
- `AUTOLOOP.md` (metodología) y CI con la suite de pruebas.

## [0.1.0]

- MVP conforme a la Especificación Técnica Mínima: carga PDF/DOCX/TXT/MD,
  extracción + OCR local, limpieza, segmentación por capítulos, prompts,
  consolidación, productos validados y exportación MD/DOCX/Obsidian/JSON.
