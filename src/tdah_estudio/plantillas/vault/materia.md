---
tipo: sistema
tags: [sistema, ${materia_min}]
---

# ${emoji} ${materia}

Estructura por capítulo/tema:

```
${materia}/
└── <Nombre del capítulo>/
    ├── <capítulo> — Bloque 1 de N.md   ← generados por tdah-estudio chunk
    ├── ...
    └── 🧠 Síntesis — <capítulo>.md     ← salida del LLM (3+3+1)
```

Cada bloque lleva `#bloque-20min` y su `estado:` en el frontmatter.
El dashboard los recoge automáticamente: aquí no hay que "organizar" nada.
