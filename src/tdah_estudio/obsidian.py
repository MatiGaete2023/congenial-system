"""TODO el renderizado Markdown del sistema, desde plantillas externas.

Restricción 4 del proceso v2: cero plantillas duplicadas en f-strings.
Cada nota se genera desde ``plantillas/*.md`` con ``string.Template``
(stdlib: se mantiene el requisito de cero dependencias). Las variantes
(bloque normal vs último, con o sin aviso de descanso) son PARÁMETROS
que rellenan la misma plantilla base, no copias de la plantilla.

Se usa ``Template.substitute`` (estricto) y no ``safe_substitute``: una
variable olvidada debe reventar en los tests de golden files, no producir
una nota con un ``${hueco}`` visible que el estudiante descubra a mitad
de un bloque de estudio.

ARQUITECTURA DEL VAULT — lógica neurocognitiva:

* Tags por ENERGÍA y no solo por tema (#baja-energia / #alta-energia): la
  disponibilidad ejecutiva en TDAH fluctúa de forma poco predecible durante
  el día. Etiquetar por costo energético permite preguntar "¿qué puedo hacer
  AHORA con la energía que tengo?" en vez de "¿qué toca?" — la segunda
  pregunta produce parálisis y culpa; la primera produce acción.
* #bloque-20min como contrato temporal: ver el tag ya responde la pregunta
  paralizante "¿cuánto me va a costar esto?".
* #recompensa-dopamina como paso EXPLÍCITO del flujo: en cerebros
  neurotípicos la sensación de tarea-completada refuerza sola; en TDAH esa
  señal interna es débil y se protetiza con recompensa externa pactada
  ANTES (elegirla después añade una decisión en el momento de menor
  energía disponible).
* Dashboard con Dataview: estado del sistema SIEMPRE visible sin
  reconstruirlo mentalmente; elimina el "¿dónde estaba?" que consume los
  primeros 10 minutos de cada sesión.
"""

from __future__ import annotations

import re
from datetime import date
from importlib.resources import files
from pathlib import Path
from string import Template
from typing import Any

from tdah_estudio.chunker import BloqueEstudio
from tdah_estudio.config import ConfigTDAH


def _plantilla(nombre: str) -> Template:
    """Carga una plantilla empaquetada (funciona instalada y desde el repo).

    joinpath se encadena parte a parte: Traversable.joinpath acepta un solo
    segmento en Python 3.9, y ``nombre`` puede traer subcarpeta ("vault/x.md").
    """
    recurso = files("tdah_estudio").joinpath("plantillas")
    for parte in Path(nombre).parts:
        recurso = recurso.joinpath(parte)
    return Template(recurso.read_text(encoding="utf-8"))


def slug(texto: str) -> str:
    """Título -> nombre de archivo seguro y estable (conserva acentos)."""
    limpio = re.sub(r"[^\w\sáéíóúüñÁÉÍÓÚÜÑ-]", "", texto, flags=re.UNICODE)
    return re.sub(r"\s+", " ", limpio).strip()


def nombre_archivo_bloque(bloque: BloqueEstudio) -> str:
    """Nombre canónico del archivo de un bloque; los enlaces [[...]] entre
    bloques dependen de que este nombre sea EXACTAMENTE reproducible."""
    return f"{slug(bloque.titulo_fuente)} — Bloque {bloque.indice} de {bloque.total}.md"


# ======================================================================
# Render de bloques de estudio
# ======================================================================
def render_bloque(
    bloque: BloqueEstudio, cfg: ConfigTDAH, fecha: date | None = None
) -> str:
    """Nota Obsidian de un bloque, con estructura fija en 4 zonas.

    La predictibilidad estructural reduce el costo de "orientación" al
    abrir la nota: el cerebro TDAH gasta recursos ejecutivos escasos en
    decidir "por dónde empiezo"; una plantilla idéntica elimina esa
    decisión (automatización del arranque). El parámetro ``fecha`` existe
    para que los golden files de los tests sean deterministas.
    """
    fecha_str = (fecha or date.today()).isoformat()
    es_ultimo = bloque.indice == bloque.total

    if es_ultimo:
        cierre = _plantilla("bloque_cierre_ultimo.md").substitute(
            titulo_fuente=bloque.titulo_fuente,
            total=bloque.total,
            minutos_totales=bloque.total * cfg.minutos_por_bloque,
        )
    else:
        aviso = ""
        if bloque.es_fin_de_sesion:
            aviso = _plantilla("bloque_aviso_descanso.md").substitute(
                bloques_sesion=cfg.bloques_por_sesion_max,
                minutos_descanso=cfg.minutos_descanso_largo,
            )
        siguiente = (
            f"{slug(bloque.titulo_fuente)} — Bloque {bloque.indice + 1} de {bloque.total}"
        )
        cierre = _plantilla("bloque_cierre_normal.md").substitute(
            minutos_pausa=cfg.minutos_pausa_corta,
            aviso_descanso=aviso,
            enlace_siguiente=siguiente,
        )

    barra = "█" * bloque.indice + "░" * (bloque.total - bloque.indice)
    return _plantilla("bloque.md").substitute(
        titulo_fuente=bloque.titulo_fuente,
        indice=bloque.indice,
        total=bloque.total,
        sesion=bloque.sesion,
        palabras=bloque.palabras,
        minutos=bloque.minutos_estimados,
        fecha=fecha_str,
        sufijo_ultimo=" (ÚLTIMO)" if es_ultimo else "",
        barra=barra,
        minutos_bloque=cfg.minutos_por_bloque,
        minutos_lectura=cfg.minutos_lectura_efectiva,
        minutos_pausa=cfg.minutos_pausa_corta,
        texto=bloque.texto,
        cierre=cierre,
    )


# ======================================================================
# Render de la síntesis LLM (3 viñetas + 3 recall + 1 Feynman)
# ======================================================================
def render_sintesis(
    datos: dict[str, Any], fuente: str, fecha: date | None = None
) -> str:
    """Convierte el JSON YA VALIDADO del LLM en nota Obsidian de síntesis.

    Precondición: ``datos`` pasó por ``prompts.validar_respuesta``. Este
    renderizador no re-valida: una sola fuente de verdad para el contrato.
    """
    fecha_str = (fecha or date.today()).isoformat()
    tags = "\n".join(
        f"  - {t}" for t in ["sintesis", *datos.get("tags_sugeridos", [])]
    )
    vinetas = "\n".join(f"- {v}" for v in datos["resumen_ejecutivo"])
    preguntas = "\n\n".join(
        f"**P{i}. {q['pregunta']}**\n"
        f"> [!hint]- Pista\n> {q['pista']}\n\n"
        f"> [!check]- Respuesta modelo\n> {q['respuesta_modelo']}"
        for i, q in enumerate(datos["active_recall"], 1)
    )
    aviso_crudo = datos.get("aviso_cobertura")
    aviso = (
        f"\n> [!warning] Cobertura parcial\n> {aviso_crudo}\n"
        if aviso_crudo and str(aviso_crudo).lower() != "null"
        else ""
    )
    feynman = datos["analogia_feynman"]
    return _plantilla("sintesis.md").substitute(
        fuente=fuente,
        dificultad=datos.get("dificultad_percibida", "media"),
        fecha=fecha_str,
        tags=tags,
        titulo=datos["titulo_unidad"],
        aviso=aviso,
        vinetas=vinetas,
        preguntas=preguntas,
        concepto=feynman["concepto_original"],
        analogia=feynman["analogia"],
        donde_se_rompe=feynman["donde_se_rompe"],
    )


# ======================================================================
# Generación del vault completo
# ======================================================================
class ExportadorObsidian:
    """Crea/repone la estructura del vault: carpetas, plantillas, dashboard.

    Idempotente por contrato: SOLO escribe archivos de sistema (dashboard,
    reglas, READMEs, plantillas), que siempre se reponen a su estado
    canónico. Las notas del usuario viven en otras rutas y jamás se tocan:
    perder apuntes por re-ejecutar un comando destruiría la confianza en
    el sistema, y la confianza es lo que sostiene el hábito.
    """

    def __init__(self, cfg: ConfigTDAH | None = None):
        self.cfg = cfg or ConfigTDAH()

    # ------------------------------------------------------------------ #
    def _contenidos(self) -> dict[str, str]:
        """Mapa ruta-relativa -> contenido renderizado de cada archivo de sistema."""
        cfg = self.cfg
        comunes = {
            "minutos_por_bloque": cfg.minutos_por_bloque,
            "minutos_lectura_efectiva": cfg.minutos_lectura_efectiva,
            "minutos_pausa_corta": cfg.minutos_pausa_corta,
            "minutos_descanso_largo": cfg.minutos_descanso_largo,
            "bloques_por_sesion_max": cfg.bloques_por_sesion_max,
            "max_ideas_por_bloque": cfg.max_ideas_por_bloque,
        }
        lineas_bloques = "\n".join(
            f"- [ ] Bloque {n}: [[ ]] #bloque-20min"
            for n in range(1, cfg.bloques_por_sesion_max + 1)
        )
        return {
            "00 - Inicio/🏠 Dashboard.md": _plantilla("vault/dashboard.md").substitute(comunes),
            "00 - Inicio/📜 Reglas del sistema.md": _plantilla("vault/reglas.md").substitute(
                comunes
            ),
            "01 - Bandeja de entrada/README.md": _plantilla("vault/bandeja.md").substitute(),
            "02 - Derecho/README.md": _plantilla("vault/materia.md").substitute(
                materia="Derecho", materia_min="derecho", emoji="⚖️"
            ),
            "03 - Historia/README.md": _plantilla("vault/materia.md").substitute(
                materia="Historia", materia_min="historia", emoji="🏛️"
            ),
            "04 - Síntesis LLM/README.md": _plantilla("vault/sintesis_readme.md").substitute(),
            "05 - Repaso espaciado/README.md": _plantilla("vault/repaso.md").substitute(),
            "99 - Plantillas/Plantilla - Bloque 15min.md": _plantilla(
                "vault/tpl_bloque.md"
            ).substitute(comunes),
            "99 - Plantillas/Plantilla - Concepto jurídico.md": _plantilla(
                "vault/tpl_derecho.md"
            ).substitute(comunes),
            "99 - Plantillas/Plantilla - Evento histórico.md": _plantilla(
                "vault/tpl_historia.md"
            ).substitute(),
            "99 - Plantillas/Plantilla - Sesión diaria.md": _plantilla(
                "vault/tpl_sesion.md"
            ).substitute(dict(comunes, lineas_bloques=lineas_bloques)),
        }

    def generar(self, raiz: Path) -> list[Path]:
        """Escribe el vault en ``raiz`` y devuelve las rutas escritas."""
        escritas = []
        for rel, contenido in self._contenidos().items():
            destino = raiz / rel
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(contenido, encoding="utf-8")
            escritas.append(destino)
        return escritas
