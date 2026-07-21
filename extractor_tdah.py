#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
 PLANTILLA DE EXTRACCIÓN DE CONOCIMIENTO PARA TDAH (Presentación Inatenta)
===============================================================================
 Sistema automatizado de organización de estudio para Derecho e Historia.

 Módulos incluidos (los tres son autocontenidos y funcionan sin red):

   1. MicroChunker      -> Divide capítulos densos en bloques exactos de 15 min.
   2. GeneradorPrompt   -> Produce el System Prompt reutilizable para APIs LLM
                           (resumen 3 viñetas + 3 preguntas Active Recall +
                           1 analogía Feynman) y el payload de ejemplo.
   3. ExportadorObsidian-> Genera el vault Markdown con tags TDAH
                           (#baja-energia, #bloque-20min, #recompensa-dopamina).

 Uso rápido (CLI):
   python extractor_tdah.py demo                       # todo con texto de ejemplo
   python extractor_tdah.py chunk capitulo.txt         # trocear un capítulo
   python extractor_tdah.py prompt                     # imprimir system prompt
   python extractor_tdah.py vault --salida mi_vault    # generar vault Obsidian

 Requisitos: Python 3.9+. Sin dependencias externas obligatorias.
 Opcional: `pypdf` para leer PDFs directamente (import protegido).

-------------------------------------------------------------------------------
 FUNDAMENTO NEUROCIENTÍFICO GENERAL (por qué existe este archivo)
-------------------------------------------------------------------------------
 El TDAH inatento no es un déficit de conocimiento sino de *gestión ejecutiva*
 del conocimiento. Tres hallazgos guían todo el diseño de este script:

 a) MEMORIA DE TRABAJO REDUCIDA (modelo de Baddeley): el "bucle fonológico" y
    la "agenda visoespacial" retienen menos elementos simultáneos y por menos
    tiempo. Un capítulo de 40 páginas de Historia Constitucional excede esa
    capacidad por un factor de 20-50x. Solución: fragmentar la entrada hasta
    que cada unidad quepa COMPLETA en memoria de trabajo (bloques de 15 min,
    ~4-6 ideas nuevas por bloque). Nada de "recuerda lo del capítulo 2":
    cada bloque re-declara su propio contexto.

 b) SISTEMA DOPAMINÉRGICO HIPOACTIVO (circuito frontoestriatal): la corteza
    prefrontal recibe menos señal de recompensa anticipada, por lo que las
    tareas largas sin hitos intermedios "no registran" progreso y el cerebro
    abandona. Solución: cada bloque termina con una recompensa explícita y
    un marcador de progreso visible (checkbox, contador X/N, tag
    #recompensa-dopamina). El progreso invisible es progreso inexistente
    para un cerebro TDAH.

 c) CEGUERA TEMPORAL (time blindness): la estimación subjetiva de duración
    está distorsionada; "estudiar la tarde" es un horizonte sin bordes que
    dispara evitación. Solución: unidades de tiempo EXACTAS y pequeñas
    (15 minutos), calculadas programáticamente a partir de la velocidad
    real de lectura, nunca "hasta que termines".

 Cada clase repite y amplía estas notas donde aplican.
===============================================================================
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import textwrap
from dataclasses import dataclass, field, asdict
from datetime import date
from pathlib import Path
from typing import List, Optional

# ---------------------------------------------------------------------------
# Import opcional y protegido: lectura directa de PDF si pypdf está instalado.
# Se protege para que el script NUNCA falle por una dependencia ausente:
# para un usuario con TDAH, un traceback de ImportError en el primer intento
# de uso es fricción suficiente para abandonar la herramienta (la barrera de
# inicio es el punto de fallo ejecutivo número uno en TDAH inatento).
# ---------------------------------------------------------------------------
try:
    from pypdf import PdfReader  # type: ignore
    _PDF_DISPONIBLE = True
except ImportError:
    _PDF_DISPONIBLE = False


# =============================================================================
# CONFIGURACIÓN CENTRAL
# =============================================================================
@dataclass
class ConfigTDAH:
    """Parámetros calibrados para lectura densa (jurídica/histórica) con TDAH.

    NEUROCIENCIA — por qué estos números y no otros:

    * ppm_lectura_densa = 110
      Un adulto promedio lee prosa general a 200-250 palabras/minuto (ppm).
      Texto jurídico/histórico denso baja a ~150 ppm por carga sintáctica
      (subordinadas, latinismos, referencias cruzadas). En TDAH inatento se
      aplica un descuento adicional de ~25-30% por relecturas involuntarias
      (el "mind-wandering" obliga a releer párrafos ya vistos: la atención
      sostenida decae en ondas de 8-12 minutos). 110 ppm es la tasa EFECTIVA
      conservadora: preferimos bloques que sobren a bloques que desborden,
      porque terminar antes de tiempo genera sensación de victoria (dopamina)
      y desbordar genera frustración (cortisol -> evitación futura).

    * minutos_por_bloque = 15
      La atención sostenida sin estimulación externa en TDAH colapsa de forma
      medible entre los 10 y los 20 minutos. 15 minutos se sitúa dentro de la
      ventana segura Y es divisor exacto de la hora, lo que simplifica el
      cálculo mental de planificación (4 bloques = 1 hora): reducir carga de
      cálculo es reducir carga ejecutiva.

    * minutos_lectura_efectiva = 11
      De los 15 minutos del bloque, solo 11 son lectura. Los 4 restantes se
      reservan DENTRO del bloque para: 2 min de recuperación activa (escribir
      de memoria lo leído, efecto testing de Roediger & Karpicke: recuperar
      consolida más que releer) + 2 min de recompensa/pausa. Si la recompensa
      viviera "fuera" del bloque, el cerebro TDAH la descontaría como lejana
      y perdería su poder motivacional (descuento hiperbólico del refuerzo
      demorado, más pronunciado en TDAH).

    * max_ideas_por_bloque = 5
      La memoria de trabajo típica sostiene 4±1 "chunks" (Cowan, 2001); en
      TDAH el extremo bajo. 5 ideas es el techo: si un bloque generado supera
      esto en la fase LLM, debe subdividirse.

    * bloques_por_sesion_max = 4
      Tras ~60 minutos (4 bloques) la inhibición de distractores se agota
      (fatiga del córtex prefrontal dorsolateral). El script se niega a
      planificar sesiones más largas: el descanso largo es obligatorio.
    """
    ppm_lectura_densa: int = 110
    minutos_por_bloque: int = 15
    minutos_lectura_efectiva: int = 11
    max_ideas_por_bloque: int = 5
    bloques_por_sesion_max: int = 4
    minutos_pausa_corta: int = 2      # dentro del bloque (recompensa inmediata)
    minutos_descanso_largo: int = 20  # tras cada sesión de 4 bloques

    @property
    def palabras_por_bloque(self) -> int:
        """Palabras que caben en la ventana de lectura efectiva de un bloque.

        110 ppm * 11 min = 1210 palabras. Este es el tamaño objetivo del
        chunk: una cantidad FINITA y VISIBLE. El estudiante nunca abre un
        bloque sin saber exactamente cuánto le queda (antídoto directo
        contra la ceguera temporal).
        """
        return self.ppm_lectura_densa * self.minutos_lectura_efectiva

    @classmethod
    def desde_json(cls, ruta: Path) -> "ConfigTDAH":
        """Carga configuración desde config_tdah.json, ignorando claves extra.

        Tolerante a errores a propósito: un JSON malformado degrada a los
        valores por defecto con un aviso, jamás a un crash. Ver nota sobre
        fricción de inicio en la cabecera de imports.
        """
        try:
            datos = json.loads(ruta.read_text(encoding="utf-8"))
            campos_validos = {k: v for k, v in datos.items()
                              if k in cls.__dataclass_fields__}
            return cls(**campos_validos)
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            print(f"[aviso] No se pudo leer {ruta} ({exc}); "
                  f"uso configuración por defecto.", file=sys.stderr)
            return cls()


# =============================================================================
# MÓDULO 1: MICRO-CHUNKER DE 15 MINUTOS
# =============================================================================
@dataclass
class BloqueEstudio:
    """Un micro-bloque de estudio de 15 minutos, autocontenido.

    Autocontenido significa: incluye su propio título, su posición en la
    serie (n_bloque/total), su recuento de palabras y su duración estimada.
    NEUROCIENCIA: la memoria de trabajo TDAH no puede sostener el contexto
    'voy por el bloque 7 de 12 del capítulo 3' entre sesiones; el bloque
    debe declararlo él mismo cada vez que se abre (estado externalizado).
    """
    indice: int
    total: int
    titulo_fuente: str
    texto: str
    palabras: int
    minutos_estimados: float
    sesion: int          # a qué sesión de 4 bloques pertenece
    es_fin_de_sesion: bool

    def a_markdown(self, cfg: ConfigTDAH) -> str:
        """Renderiza el bloque como nota Obsidian lista para estudiar.

        Estructura fija en 4 zonas, siempre en el mismo orden. La
        predictibilidad estructural reduce el costo de 'orientación' al
        abrir la nota: el cerebro TDAH gasta recursos ejecutivos escasos
        en decidir 'por dónde empiezo'; una plantilla idéntica elimina
        esa decisión por completo (automatización del arranque).
        """
        marcador_progreso = "█" * self.indice + "░" * (self.total - self.indice)
        aviso_descanso = ""
        if self.es_fin_de_sesion:
            aviso_descanso = (
                f"\n> [!success] FIN DE SESIÓN — descanso largo obligatorio\n"
                f"> Has completado {cfg.bloques_por_sesion_max} bloques. "
                f"Descansa {cfg.minutos_descanso_largo} min SIN pantallas de texto.\n"
                f"> Tu córtex prefrontal necesita reponer capacidad de "
                f"inhibición antes de la siguiente sesión.\n"
            )
        return f"""---
tipo: bloque-estudio
fuente: "{self.titulo_fuente}"
bloque: {self.indice}
total_bloques: {self.total}
sesion: {self.sesion}
palabras: {self.palabras}
minutos: {self.minutos_estimados}
fecha_creacion: {date.today().isoformat()}
estado: pendiente
tags:
  - bloque-20min
  - micro-learning
---

# {self.titulo_fuente} — Bloque {self.indice} de {self.total}

`{marcador_progreso}` **{self.indice}/{self.total}**

> [!timer] Este bloque dura {cfg.minutos_por_bloque} minutos exactos
> - {cfg.minutos_lectura_efectiva} min de lectura ({self.palabras} palabras)
> - 2 min de recuperación activa (sección "Cierre" abajo)
> - {cfg.minutos_pausa_corta} min de recompensa #recompensa-dopamina
>
> Pon un temporizador FÍSICO ahora. No empieces sin temporizador.

## 📖 Lectura

{self.texto}

## ✍️ Cierre — recuperación activa (2 min, sin mirar arriba)

Escribe de memoria, en una frase cada una:

- La idea principal de este bloque fue: ...
- Un dato/fecha/artículo concreto que apareció: ...
- Esto se conecta con: [[ ]]

## 🎁 Recompensa (2 min) #recompensa-dopamina

- [ ] Marca este bloque como hecho: cambia `estado: pendiente` a `estado: completado`
- [ ] Recompensa elegida ANTES de empezar: _______
{aviso_descanso}
**Siguiente:** [[{_slug(self.titulo_fuente)} — Bloque {self.indice + 1} de {self.total}]]
""" if self.indice < self.total else f"""---
tipo: bloque-estudio
fuente: "{self.titulo_fuente}"
bloque: {self.indice}
total_bloques: {self.total}
sesion: {self.sesion}
palabras: {self.palabras}
minutos: {self.minutos_estimados}
fecha_creacion: {date.today().isoformat()}
estado: pendiente
tags:
  - bloque-20min
  - micro-learning
---

# {self.titulo_fuente} — Bloque {self.indice} de {self.total} (ÚLTIMO)

`{marcador_progreso}` **{self.indice}/{self.total}**

> [!timer] Este bloque dura {cfg.minutos_por_bloque} minutos exactos
> - {cfg.minutos_lectura_efectiva} min de lectura ({self.palabras} palabras)
> - 2 min de recuperación activa
> - {cfg.minutos_pausa_corta} min de recompensa #recompensa-dopamina

## 📖 Lectura

{self.texto}

## ✍️ Cierre — recuperación activa (2 min, sin mirar arriba)

- La idea principal de este bloque fue: ...
- Un dato/fecha/artículo concreto que apareció: ...
- Esto se conecta con: [[ ]]

## 🏆 Capítulo COMPLETO #recompensa-dopamina

- [ ] Cambia `estado:` a `completado`
- [ ] Recompensa GRANDE (elegida antes de empezar el capítulo): _______
- [ ] Programa el repaso espaciado: crea nota con tag #repaso-48h para pasado mañana

> [!success] Terminaste "{self.titulo_fuente}": {self.total} bloques, \
~{self.total * cfg.minutos_por_bloque} minutos de estudio real y medible.
"""


def _slug(texto: str) -> str:
    """Convierte un título en nombre de archivo seguro y estable."""
    limpio = re.sub(r"[^\w\sáéíóúüñÁÉÍÓÚÜÑ-]", "", texto, flags=re.UNICODE)
    return re.sub(r"\s+", " ", limpio).strip()


class MicroChunker:
    """Divide un texto largo en bloques exactos de 15 minutos de estudio.

    ALGORITMO (3 pasos):
      1. Segmentar el texto en párrafos (unidad semántica mínima que nunca
         se rompe: cortar a mitad de párrafo destruye la coherencia local,
         y la memoria de trabajo TDAH depende de que cada unidad sea
         semánticamente cerrada).
      2. Empaquetar párrafos consecutivos con algoritmo greedy hasta
         acercarse a `palabras_por_bloque` (1210 por defecto). Un párrafo
         que por sí solo excede el presupuesto se subdivide por oraciones.
      3. Balancear: si el último bloque queda < 40% del presupuesto, se
         redistribuye con el anterior para evitar un "bloque enano" final
         (un bloque de 3 minutos rompe el contrato temporal de 15 min y
         el contrato roto erosiona la confianza en el sistema — la
         consistencia del ritual es lo que lo vuelve automático).
    """

    # Corte de oraciones consciente de abreviaturas frecuentes en texto
    # jurídico/histórico español: evita cortar en "art. 19" o "S.XIX".
    _ABREVIATURAS = r"(?<!\bart)(?<!\bArt)(?<!\binc)(?<!\bnúm)(?<!\bpág)" \
                    r"(?<!\bSr)(?<!\bSra)(?<!\bDr)(?<!\bDra)(?<!\bS)(?<!\bN)"
    _RE_ORACION = re.compile(_ABREVIATURAS + r"\.\s+(?=[A-ZÁÉÍÓÚÜÑ¿¡])")

    def __init__(self, cfg: Optional[ConfigTDAH] = None):
        self.cfg = cfg or ConfigTDAH()

    # ------------------------------------------------------------------ #
    def dividir(self, texto: str, titulo_fuente: str) -> List[BloqueEstudio]:
        """Devuelve la lista de BloqueEstudio para un capítulo completo."""
        parrafos = self._segmentar_parrafos(texto)
        if not parrafos:
            raise ValueError(
                "El texto está vacío tras la limpieza; revisa el archivo de "
                "entrada (¿es un PDF escaneado sin capa de texto?)."
            )
        paquetes = self._empaquetar(parrafos)
        paquetes = self._balancear_ultimo(paquetes)
        return self._materializar(paquetes, titulo_fuente)

    # ------------------------------------------------------------------ #
    def _segmentar_parrafos(self, texto: str) -> List[str]:
        """Normaliza saltos de línea y separa por párrafos reales."""
        texto = texto.replace("\r\n", "\n").replace("\r", "\n")
        # Los PDFs jurídicos suelen romper líneas a mitad de oración:
        # una línea sola NO es un párrafo; el separador real es línea en blanco.
        crudos = re.split(r"\n\s*\n", texto)
        parrafos = []
        for p in crudos:
            unificado = re.sub(r"\s+", " ", p).strip()
            if len(unificado.split()) >= 3:  # descarta ruido (números de página)
                parrafos.append(unificado)
        return parrafos

    def _dividir_parrafo_gigante(self, parrafo: str) -> List[str]:
        """Subdivide por oraciones un párrafo que excede el presupuesto solo."""
        oraciones = self._RE_ORACION.split(parrafo)
        presupuesto = self.cfg.palabras_por_bloque
        trozos, actual, cuenta = [], [], 0
        for o in oraciones:
            n = len(o.split())
            if cuenta + n > presupuesto and actual:
                trozos.append(" ".join(actual))
                actual, cuenta = [], 0
            actual.append(o if o.endswith((".", "?", "!", ":")) else o + ".")
            cuenta += n
        if actual:
            trozos.append(" ".join(actual))
        return trozos

    def _empaquetar(self, parrafos: List[str]) -> List[List[str]]:
        """Greedy: agrupa párrafos hasta llenar el presupuesto de palabras."""
        presupuesto = self.cfg.palabras_por_bloque
        paquetes: List[List[str]] = []
        actual: List[str] = []
        cuenta = 0
        for p in parrafos:
            n = len(p.split())
            if n > presupuesto:
                # Párrafo monstruo (típico en sentencias judiciales): cerrar
                # el paquete actual y trocear el monstruo por oraciones.
                if actual:
                    paquetes.append(actual)
                    actual, cuenta = [], 0
                for trozo in self._dividir_parrafo_gigante(p):
                    paquetes.append([trozo])
                continue
            if cuenta + n > presupuesto and actual:
                paquetes.append(actual)
                actual, cuenta = [], 0
            actual.append(p)
            cuenta += n
        if actual:
            paquetes.append(actual)
        return paquetes

    def _balancear_ultimo(self, paquetes: List[List[str]]) -> List[List[str]]:
        """Fusiona un último bloque enano (<40% presupuesto) con el anterior,
        siempre que el resultado no supere el 120% del presupuesto (un ligero
        sobrecosto final es preferible a un bloque ridículo de 3 minutos)."""
        if len(paquetes) < 2:
            return paquetes
        presupuesto = self.cfg.palabras_por_bloque
        ultimo = sum(len(p.split()) for p in paquetes[-1])
        penultimo = sum(len(p.split()) for p in paquetes[-2])
        if ultimo < presupuesto * 0.4 and (ultimo + penultimo) <= presupuesto * 1.2:
            paquetes[-2].extend(paquetes[-1])
            paquetes.pop()
        return paquetes

    def _materializar(self, paquetes: List[List[str]],
                      titulo: str) -> List[BloqueEstudio]:
        """Convierte paquetes de párrafos en objetos BloqueEstudio numerados."""
        total = len(paquetes)
        bloques = []
        for i, paquete in enumerate(paquetes, start=1):
            texto = "\n\n".join(paquete)
            palabras = len(texto.split())
            minutos = round(palabras / self.cfg.ppm_lectura_densa, 1)
            sesion = math.ceil(i / self.cfg.bloques_por_sesion_max)
            fin_sesion = (i % self.cfg.bloques_por_sesion_max == 0) and i < total
            bloques.append(BloqueEstudio(
                indice=i, total=total, titulo_fuente=titulo, texto=texto,
                palabras=palabras, minutos_estimados=minutos,
                sesion=sesion, es_fin_de_sesion=fin_sesion,
            ))
        return bloques

    # ------------------------------------------------------------------ #
    def resumen_plan(self, bloques: List[BloqueEstudio]) -> str:
        """Tabla de planificación imprimible: el mapa completo ANTES de empezar.

        NEUROCIENCIA: mostrar el costo total por adelantado ('12 bloques =
        3 sesiones = 3 días a 1 sesión/día') convierte una tarea amorfa en
        un contrato finito. La evitación TDAH se dispara ante lo indefinido,
        no ante lo grande: lo grande-pero-acotado es abordable."""
        total_min = len(bloques) * self.cfg.minutos_por_bloque
        sesiones = math.ceil(len(bloques) / self.cfg.bloques_por_sesion_max)
        lineas = [
            f"PLAN DE ESTUDIO — {bloques[0].titulo_fuente}",
            f"  Bloques de {self.cfg.minutos_por_bloque} min : {len(bloques)}",
            f"  Sesiones (máx {self.cfg.bloques_por_sesion_max} bloques): {sesiones}",
            f"  Tiempo total real           : {total_min} min "
            f"(~{total_min / 60:.1f} h repartidas, NO seguidas)",
            "",
            f"  {'#':>3} {'palabras':>9} {'min':>5}  sesión",
        ]
        for b in bloques:
            marca = "  <- descanso largo después" if b.es_fin_de_sesion else ""
            lineas.append(f"  {b.indice:>3} {b.palabras:>9} "
                          f"{b.minutos_estimados:>5}  S{b.sesion}{marca}")
        return "\n".join(lineas)


# =============================================================================
# MÓDULO 2: SYSTEM PROMPT REUTILIZABLE PARA APIs DE LLM
# =============================================================================
class GeneradorPrompt:
    """Construye el System Prompt hiper-detallado y el payload de ejemplo.

    El prompt está versionado y parametrizado (materia, nivel) para que el
    MISMO prompt sirva para Derecho e Historia sin edición manual: editar
    prompts a mano cada vez es exactamente el tipo de fricción repetitiva
    que un sistema para TDAH debe eliminar (cada decisión evitada es
    capacidad ejecutiva conservada para el estudio en sí).
    """

    VERSION = "1.2.0"

    # ------------------------------------------------------------------ #
    @staticmethod
    def system_prompt(materia: str = "Derecho e Historia",
                      idioma: str = "español") -> str:
        """El System Prompt completo, listo para pegar en cualquier API.

        DISEÑO DEL PROMPT — decisiones y su razón neurocognitiva:
        - Salida en JSON estricto: la estructura fija permite volcar la
          respuesta directamente a la plantilla Obsidian sin reformateo
          manual (cero fricción post-proceso).
        - Exactamente 3 viñetas / 3 preguntas / 1 analogía: los límites
          duros existen porque 'resume esto' sin cota produce muros de
          texto que reintroducen el problema original. 3 elementos caben
          en memoria de trabajo TDAH; 7 no.
        - Viñetas de máximo 25 palabras: una viñeta que hay que releer
          no es una viñeta.
        - Preguntas de recuperación (Active Recall) y no de reconocimiento:
          el efecto testing (Roediger & Karpicke, 2006) muestra que intentar
          RECUPERAR consolida la memoria a largo plazo mucho más que releer;
          en TDAH además convierte el repaso pasivo (donde la mente se fuga)
          en tarea activa con feedback inmediato (micro-dopamina por acierto).
        - Analogía Feynman con objeto cotidiano: la codificación dual y el
          anclaje a conocimiento previo crean una ruta de recuperación
          alternativa cuando el término técnico no aparece ('¿cómo era lo
          del portero del edificio?' -> control de constitucionalidad).
        """
        return f"""\
Eres "Procesador de Estudio TDAH v{GeneradorPrompt.VERSION}", un asistente experto en
pedagogía para estudiantes con TDAH de presentación inatenta y en análisis de
textos académicos de {materia}. Trabajas siempre en {idioma}.

== TU TAREA ==
Recibirás el texto de un documento extenso y denso (capítulo, sentencia, ley,
manual). Debes transformarlo en una unidad de estudio apta para memoria de
trabajo reducida. Tu salida se inserta automáticamente en una plantilla, por
lo que el formato es OBLIGATORIO e innegociable.

== REGLAS DE PROCESAMIENTO ==
1. Lee el documento completo antes de escribir nada.
2. Identifica las 3 ideas con mayor probabilidad de aparecer en un examen
   (criterio: definiciones operativas, fechas-bisagra, requisitos/elementos
   de instituciones jurídicas, relaciones causa-efecto históricas).
3. Ignora por completo: notas al pie ornamentales, citas de cortesía,
   digresiones del autor. El estudiante NO puede permitirse ruido.
4. Nunca uses frases de relleno ("es importante destacar", "cabe señalar").
   Cada palabra que no informa, estorba.
5. Si el documento excede una unidad temática coherente, procesa SOLO la
   principal e indícalo en "aviso_cobertura".

== FORMATO DE SALIDA (JSON estricto, sin texto fuera del JSON) ==
{{
  "titulo_unidad": "máximo 8 palabras, sin subtítulos",
  "resumen_ejecutivo": [
    "Viñeta 1: la tesis central del documento. Máximo 25 palabras.",
    "Viñeta 2: el mecanismo, requisito o proceso clave. Máximo 25 palabras.",
    "Viñeta 3: la consecuencia, excepción o dato-bisagra. Máximo 25 palabras."
  ],
  "active_recall": [
    {{
      "pregunta": "Pregunta de RECUPERACIÓN (empieza con Explica/Enumera/Compara/Por qué). Prohibido verdadero-falso y opción múltiple.",
      "respuesta_modelo": "Respuesta completa en máximo 40 palabras.",
      "pista": "Pista de una frase para desbloqueo sin revelar la respuesta."
    }},
    {{ "pregunta": "...", "respuesta_modelo": "...", "pista": "..." }},
    {{ "pregunta": "...", "respuesta_modelo": "...", "pista": "..." }}
  ],
  "analogia_feynman": {{
    "concepto_original": "El concepto más abstracto del documento.",
    "analogia": "Explicación con un objeto/situación de la vida doméstica cotidiana (cocina, edificio, fútbol, supermercado). Máximo 60 palabras. Sin tecnicismos: si un niño de 12 años no lo entiende, reescríbela.",
    "donde_se_rompe": "Una frase: en qué punto la analogía deja de ser fiel al concepto real (evita falsas generalizaciones en el examen)."
  }},
  "tags_sugeridos": ["derecho|historia", "y 2-4 tags temáticos en kebab-case"],
  "dificultad_percibida": "baja|media|alta",
  "aviso_cobertura": "null, o qué parte del documento quedó fuera y por qué"
}}

== CRITERIOS DE CALIDAD (autoverifica antes de responder) ==
- ¿Cada viñeta sobrevive sola, sin las otras dos? Debe hacerlo.
- ¿Las 3 preguntas cubren las 3 viñetas (una por viñeta)? Deben hacerlo.
- ¿La analogía usa SOLO vocabulario cotidiano? Debe hacerlo.
- ¿El JSON es parseable? Verifica comillas y comas antes de emitir.
"""

    # ------------------------------------------------------------------ #
    @staticmethod
    def payload_ejemplo(texto_documento: str,
                        materia: str = "Derecho") -> dict:
        """Payload listo para la Messages API de Anthropic (u homóloga).

        Se emite como dict serializable: `json.dumps(payload)` es el cuerpo
        HTTP. max_tokens generoso porque el JSON de salida con 3 respuestas
        modelo ronda 600-900 tokens; temperature baja (0.2) porque queremos
        extracción fiel, no creatividad — la única sección "creativa" es la
        analogía y el prompt ya la acota estructuralmente.
        """
        return {
            "model": "claude-sonnet-5",
            "max_tokens": 2048,
            "temperature": 0.2,
            "system": GeneradorPrompt.system_prompt(materia=materia),
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Procesa el siguiente documento según tus reglas y "
                        "devuelve únicamente el JSON:\n\n<documento>\n"
                        f"{texto_documento}\n</documento>"
                    ),
                }
            ],
        }

    # ------------------------------------------------------------------ #
    @staticmethod
    def validar_respuesta(json_crudo: str) -> dict:
        """Valida la respuesta del LLM contra el contrato del prompt.

        Falla con mensajes accionables (qué campo, qué se esperaba): si el
        pipeline se rompe en silencio, el estudiante pierde la sesión de
        estudio depurando — el peor resultado posible para TDAH.
        """
        try:
            datos = json.loads(json_crudo)
        except json.JSONDecodeError as exc:
            raise ValueError(f"El LLM no devolvió JSON válido: {exc}") from exc

        errores = []
        resumen = datos.get("resumen_ejecutivo")
        if not isinstance(resumen, list) or len(resumen) != 3:
            errores.append("'resumen_ejecutivo' debe ser lista de exactamente 3 viñetas")
        else:
            for i, v in enumerate(resumen, 1):
                if len(str(v).split()) > 30:  # margen sobre las 25 pactadas
                    errores.append(f"viñeta {i} excede 30 palabras")

        recall = datos.get("active_recall")
        if not isinstance(recall, list) or len(recall) != 3:
            errores.append("'active_recall' debe ser lista de exactamente 3 preguntas")
        else:
            for i, q in enumerate(recall, 1):
                for campo in ("pregunta", "respuesta_modelo", "pista"):
                    if not isinstance(q, dict) or not q.get(campo):
                        errores.append(f"pregunta {i}: falta campo '{campo}'")

        feynman = datos.get("analogia_feynman")
        if not isinstance(feynman, dict):
            errores.append("falta 'analogia_feynman'")
        else:
            for campo in ("concepto_original", "analogia", "donde_se_rompe"):
                if not feynman.get(campo):
                    errores.append(f"analogia_feynman: falta campo '{campo}'")

        if errores:
            raise ValueError("Respuesta LLM fuera de contrato: " + "; ".join(errores))
        return datos

    # ------------------------------------------------------------------ #
    @staticmethod
    def respuesta_a_markdown(datos: dict, fuente: str) -> str:
        """Convierte el JSON validado del LLM en nota Obsidian de síntesis."""
        tags = "\n".join(f"  - {t}" for t in datos.get("tags_sugeridos", []))
        vinetas = "\n".join(f"- {v}" for v in datos["resumen_ejecutivo"])
        preguntas = "\n\n".join(
            f"**P{i}. {q['pregunta']}**\n"
            f"> [!hint]- Pista\n> {q['pista']}\n\n"
            f"> [!check]- Respuesta modelo\n> {q['respuesta_modelo']}"
            for i, q in enumerate(datos["active_recall"], 1)
        )
        f = datos["analogia_feynman"]
        aviso = datos.get("aviso_cobertura")
        seccion_aviso = (
            f"\n> [!warning] Cobertura parcial\n> {aviso}\n" if aviso and aviso != "null" else ""
        )
        return f"""---
tipo: sintesis-llm
fuente: "{fuente}"
dificultad: {datos.get('dificultad_percibida', 'media')}
fecha: {date.today().isoformat()}
proximo_repaso: ""
tags:
  - sintesis
{tags}
---

# 🧠 {datos['titulo_unidad']}
{seccion_aviso}
## Resumen ejecutivo (3 ideas, nada más)

{vinetas}

## 🎯 Active Recall — responde ANTES de abrir los desplegables

{preguntas}

## 🪄 Analogía Feynman

**{f['concepto_original']}** es como...

> {f['analogia']}

⚠️ *Dónde se rompe la analogía:* {f['donde_se_rompe']}

---
- [ ] Repaso 1 (48 h) — fecha: __ #repaso-48h
- [ ] Repaso 2 (7 días) — fecha: __
- [ ] Repaso 3 (30 días) — fecha: __
"""


# =============================================================================
# MÓDULO 3: EXPORTADOR DE VAULT OBSIDIAN CON TAGS TDAH
# =============================================================================
class ExportadorObsidian:
    """Genera la estructura completa del vault: carpetas, plantillas, dashboard.

    ARQUITECTURA DEL VAULT — lógica neurocognitiva:

    * Sistema de tags por ENERGÍA y no solo por tema (#baja-energia /
      #alta-energia): la disponibilidad ejecutiva en TDAH fluctúa durante el
      día de forma poco predecible. Etiquetar tareas por costo energético
      permite preguntar "¿qué puedo hacer AHORA con la energía que tengo?"
      en lugar de "¿qué toca?" — la segunda pregunta produce parálisis y
      culpa; la primera produce acción. Repasar flashcards ya hechas es
      #baja-energia; leer un bloque nuevo de una sentencia es #alta-energia.

    * #bloque-20min como contrato temporal: el tag promete que la tarea cabe
      en un bloque corto (15 min de trabajo + margen). Ver el tag ya responde
      la pregunta paralizante "¿cuánto me va a costar esto?".

    * #recompensa-dopamina como paso EXPLÍCITO del flujo: en cerebros
      neurotípicos la sensación de tarea-completada refuerza sola; en TDAH
      esa señal interna es débil, así que se protetiza con una recompensa
      externa pactada de antemano (pactada ANTES: elegir recompensa después
      de terminar añade una decisión en el momento de menor energía).

    * Dashboard con Dataview: estado del sistema SIEMPRE visible sin
      reconstruirlo mentalmente. La nota de entrada única elimina el
      "¿dónde estaba?" que consume los primeros 10 minutos de cada sesión.
    """

    def __init__(self, cfg: Optional[ConfigTDAH] = None):
        self.cfg = cfg or ConfigTDAH()

    # ------------------------------------------------------------------ #
    def generar(self, raiz: Path) -> List[Path]:
        """Crea el vault completo en `raiz`. Devuelve las rutas escritas.

        Idempotente: re-ejecutar NO pisa notas del usuario, solo repone
        plantillas y dashboard (los archivos de sistema). Perder apuntes por
        re-ejecutar un comando sería catastrófico para la confianza."""
        estructura = {
            "00 - Inicio/🏠 Dashboard.md": self._dashboard(),
            "00 - Inicio/📜 Reglas del sistema.md": self._reglas(),
            "01 - Bandeja de entrada/README.md": self._bandeja(),
            "02 - Derecho/README.md": self._readme_materia("Derecho", "⚖️"),
            "03 - Historia/README.md": self._readme_materia("Historia", "🏛️"),
            "04 - Síntesis LLM/README.md": self._readme_sintesis(),
            "05 - Repaso espaciado/README.md": self._readme_repaso(),
            "99 - Plantillas/Plantilla - Bloque 15min.md": self._tpl_bloque(),
            "99 - Plantillas/Plantilla - Concepto jurídico.md": self._tpl_derecho(),
            "99 - Plantillas/Plantilla - Evento histórico.md": self._tpl_historia(),
            "99 - Plantillas/Plantilla - Sesión diaria.md": self._tpl_sesion(),
        }
        escritas = []
        for rel, contenido in estructura.items():
            destino = raiz / rel
            destino.parent.mkdir(parents=True, exist_ok=True)
            es_sistema = rel.startswith(("00 -", "99 -")) or rel.endswith("README.md")
            if destino.exists() and not es_sistema:
                continue  # jamás pisar contenido del usuario
            destino.write_text(contenido, encoding="utf-8")
            escritas.append(destino)
        return escritas

    # ------------------------------------------------------------------ #
    def _dashboard(self) -> str:
        return f"""---
tipo: dashboard
tags: [sistema]
---

# 🏠 Dashboard — abre SIEMPRE esta nota primero

> [!tip] Regla de oro
> No decidas qué estudiar. El dashboard decide por ti. Tú solo ejecutas
> el primer elemento de la lista que coincida con tu energía actual.

## ⚡ ¿Cuánta energía tienes AHORA MISMO?

### 🔋 Poca (cansancio, medicación en valle, tarde-noche) → #baja-energia
```dataview
TASK
FROM #baja-energia
WHERE !completed
LIMIT 3
```

### 🔋🔋🔋 Normal o alta → #alta-energia
```dataview
TASK
FROM #alta-energia
WHERE !completed
LIMIT 3
```

## ⏳ Repasos que vencen (hazlos ANTES de material nuevo)
```dataview
TABLE fuente, proximo_repaso AS "vence"
FROM #repaso-48h OR "05 - Repaso espaciado"
WHERE proximo_repaso != "" AND date(proximo_repaso) <= date(today)
SORT proximo_repaso ASC
LIMIT 5
```

## 📊 Progreso visible (dopamina de datos)
```dataview
TABLE length(rows) AS "bloques completados"
FROM "02 - Derecho" OR "03 - Historia"
WHERE estado = "completado"
GROUP BY fuente
```

## 🚦 Bloques pendientes por capítulo
```dataview
TABLE bloque + "/" + total_bloques AS "avance", minutos AS "min"
FROM #bloque-20min
WHERE estado = "pendiente"
SORT fuente ASC, bloque ASC
LIMIT 8
```

---
*Sistema de {self.cfg.minutos_por_bloque} min/bloque, máx \
{self.cfg.bloques_por_sesion_max} bloques por sesión. \
Reglas completas: [[📜 Reglas del sistema]]*
"""

    def _reglas(self) -> str:
        return f"""---
tipo: sistema
tags: [sistema]
---

# 📜 Reglas del sistema (léelas una vez; el sistema las aplica por ti)

1. **Un bloque = {self.cfg.minutos_por_bloque} minutos con temporizador físico.**
   Sin temporizador no hay bloque. La ceguera temporal del TDAH no se cura
   con voluntad, se protetiza con un reloj externo que hace el trabajo de
   percibir el tiempo por ti.

2. **Máximo {self.cfg.bloques_por_sesion_max} bloques por sesión, después
   {self.cfg.minutos_descanso_largo} min de descanso largo.** La capacidad de
   ignorar distracciones es un recurso que se agota físicamente; seguir
   "porque voy bien" hoy hipoteca la sesión de mañana.

3. **La recompensa se elige ANTES de empezar y se cobra SIEMPRE.**
   #recompensa-dopamina no es un premio moral, es neuroquímica aplicada:
   el circuito de refuerzo TDAH necesita señal externa e inmediata para
   registrar "esto valió la pena, repitámoslo".

4. **Los repasos vencidos van antes que el material nuevo.**
   La curva del olvido no negocia. 5 minutos de repaso a las 48 h ahorran
   una hora de re-aprendizaje la semana del examen.

5. **Si solo tienes energía #baja-energia, haz una tarea #baja-energia.**
   Un repaso de flashcards hecho vale infinitamente más que un bloque
   nuevo abandonado al tercer minuto. El sistema no premia la heroicidad,
   premia la constancia.

6. **Todo lo que llegue nuevo cae en [[01 - Bandeja de entrada|la bandeja]].**
   Nunca proceses en el momento de capturar: capturar y procesar son
   energías distintas.

## Vocabulario de tags

| Tag | Significado | Cuándo usarlo |
|---|---|---|
| #bloque-20min | cabe en un bloque corto con margen | toda tarea troceada |
| #baja-energia | ejecutable cansado/sin medicación | repasos, flashcards, ordenar |
| #alta-energia | requiere lectura densa nueva | bloques de lectura, síntesis |
| #recompensa-dopamina | paso de recompensa del flujo | cierre de cada bloque |
| #repaso-48h | repaso espaciado programado | tras completar una síntesis |
| #derecho / #historia | materia | toda nota de contenido |
| #examen-cerca | prioridad absoluta | 2 semanas antes del examen |
"""

    def _bandeja(self) -> str:
        return """---
tipo: sistema
tags: [sistema]
---

# 01 · Bandeja de entrada

Todo material nuevo (PDF, apunte de clase, foto de pizarra, idea suelta)
entra AQUÍ como una nota rápida, sin formato, sin pensar.

**Procesamiento (tarea #baja-energia, 1 vez al día, máx 10 min):**
1. Abre cada nota de la bandeja.
2. ¿Es un capítulo/PDF largo? → pásalo por `extractor_tdah.py chunk` y mueve
   los bloques a la carpeta de su materia.
3. ¿Es un concepto suelto? → aplica plantilla de concepto y archívalo.
4. ¿No sirve? → bórralo sin culpa.

La bandeja vacía no es la meta; la bandeja *procesada a diario* sí.
"""

    def _readme_materia(self, materia: str, emoji: str) -> str:
        return f"""---
tipo: sistema
tags: [sistema, {materia.lower()}]
---

# {emoji} {materia}

Estructura por capítulo/tema:

```
{materia}/
└── <Nombre del capítulo>/
    ├── <capítulo> — Bloque 1 de N.md   ← generados por extractor_tdah.py
    ├── ...
    └── 🧠 Síntesis — <capítulo>.md     ← salida del LLM (3+3+1)
```

Cada bloque lleva `#bloque-20min` y su `estado:` en el frontmatter.
El dashboard los recoge automáticamente: aquí no hay que "organizar" nada.
"""

    def _readme_sintesis(self) -> str:
        return """---
tipo: sistema
tags: [sistema]
---

# 04 · Síntesis LLM

Aquí viven las notas generadas con el System Prompt (resumen 3 viñetas +
3 preguntas Active Recall + analogía Feynman).

Flujo: PDF → `extractor_tdah.py prompt` → API del LLM →
`GeneradorPrompt.validar_respuesta()` → `respuesta_a_markdown()` → esta carpeta.

Regla: una síntesis por unidad temática. Si el LLM avisó `aviso_cobertura`,
crea otra unidad para lo que quedó fuera — no lo dejes implícito, tu yo
de la semana del examen no lo recordará.
"""

    def _readme_repaso(self) -> str:
        return """---
tipo: sistema
tags: [sistema]
---

# 05 · Repaso espaciado

Calendario fijo tras completar cada síntesis: **48 h → 7 días → 30 días**.

Por qué funciona (y por qué es especialmente crítico en TDAH): cada
recuperación espaciada re-consolida la traza de memoria justo cuando empieza
a decaer. Releer produce *familiaridad* ("esto me suena") que se confunde
con *saber*; en TDAH esa ilusión de competencia es más peligrosa porque la
revisión de última hora — la estrategia de rescate habitual — choca con la
dificultad de sostener maratones de atención.

Cada repaso es responder las 3 preguntas de Active Recall de la síntesis
**sin mirar**, y marcar el checkbox. 5 minutos. Tarea #baja-energia perfecta
para los valles del día.
"""

    def _tpl_bloque(self) -> str:
        cfg = self.cfg
        return f"""---
tipo: bloque-estudio
fuente: ""
bloque:
total_bloques:
minutos: {cfg.minutos_por_bloque}
estado: pendiente
tags:
  - bloque-20min
  - alta-energia
---

# {{{{title}}}}

> [!timer] {cfg.minutos_por_bloque} min: {cfg.minutos_lectura_efectiva} lectura + 2 recuperación + {cfg.minutos_pausa_corta} recompensa. Temporizador AHORA.

## 📖 Lectura

## ✍️ Cierre (2 min, de memoria)
- Idea principal:
- Dato concreto:
- Se conecta con: [[ ]]

## 🎁 #recompensa-dopamina
- [ ] `estado:` → completado
- [ ] Recompensa pactada:
"""

    def _tpl_derecho(self) -> str:
        return """---
tipo: concepto
materia: derecho
fuente: ""
dificultad: media
proximo_repaso: ""
tags:
  - derecho
  - bloque-20min
---

# ⚖️ {{title}}

**Definición en UNA frase (si no cabe en una frase, no la entiendes aún):**


**Elementos / requisitos (máx 5 — límite de memoria de trabajo):**
1.
2.
3.

**Norma / artículo exacto:**

**Analogía Feynman (objeto cotidiano):**
>

**Se conecta con:** [[ ]] · [[ ]]

**Pregunta de examen probable:**
>

---
- [ ] Repaso 48 h #repaso-48h #baja-energia
"""

    def _tpl_historia(self) -> str:
        return """---
tipo: evento
materia: historia
fuente: ""
fecha_evento: ""
dificultad: media
proximo_repaso: ""
tags:
  - historia
  - bloque-20min
---

# 🏛️ {{title}}

**Qué pasó, en UNA frase:**


**Cadena causal (la memoria TDAH retiene historias, no listas de fechas):**
```mermaid
graph LR
    A[Causa] --> B[Evento] --> C[Consecuencia]
```

**3 fechas-bisagra (máximo 3):**
| Fecha | Qué | Por qué importa |
|---|---|---|
|  |  |  |

**Analogía Feynman:**
>

**Se conecta con:** [[ ]] · [[ ]]

---
- [ ] Repaso 48 h #repaso-48h #baja-energia
"""

    def _tpl_sesion(self) -> str:
        cfg = self.cfg
        return f"""---
tipo: sesion
fecha: {{{{date}}}}
energia_inicial: ""
tags:
  - sesion-diaria
---

# 📅 Sesión {{{{date}}}}

**Energía al empezar (elige uno):** 🔋 baja / 🔋🔋 media / 🔋🔋🔋 alta
**Recompensa final pactada (escríbela ANTES del bloque 1):**

## Bloques de hoy (máx {cfg.bloques_por_sesion_max} — el sistema no negocia)
- [ ] Bloque 1: [[ ]] #bloque-20min
- [ ] Bloque 2: [[ ]] #bloque-20min
- [ ] Bloque 3: [[ ]] #bloque-20min
- [ ] Bloque 4: [[ ]] #bloque-20min
- [ ] 🎁 Recompensa cobrada #recompensa-dopamina

## Cierre (30 segundos)
**Lo que SÍ hice hoy (aunque sea 1 bloque, cuenta y se escribe):**
-

> [!success] Un bloque hecho > cuatro bloques planeados.
"""


# =============================================================================
# ENTRADA/SALIDA DE DOCUMENTOS
# =============================================================================
def leer_documento(ruta: Path) -> str:
    """Lee .txt/.md directamente y .pdf si pypdf está disponible."""
    if ruta.suffix.lower() == ".pdf":
        if not _PDF_DISPONIBLE:
            raise SystemExit(
                "Para leer PDF instala pypdf:  pip install pypdf\n"
                "Alternativa inmediata: copia el texto a un .txt y reintenta."
            )
        lector = PdfReader(str(ruta))
        paginas = [p.extract_text() or "" for p in lector.pages]
        texto = "\n\n".join(paginas)
        if len(texto.split()) < 50:
            raise SystemExit(
                f"El PDF '{ruta.name}' casi no tiene capa de texto "
                "(¿escaneado?). Pásalo por OCR antes de trocearlo."
            )
        return texto
    return ruta.read_text(encoding="utf-8", errors="replace")


TEXTO_DEMO = """\
La historia constitucional de Chile durante el siglo XIX estuvo marcada por la
búsqueda de un equilibrio entre autoridad y libertad. Tras la independencia,
los ensayos constitucionales de la década de 1820 reflejaron la tensión entre
proyectos federalistas y centralistas, ninguno de los cuales logró estabilidad
política duradera.

La Constitución de 1833, impulsada tras la victoria conservadora en Lircay,
estableció un régimen presidencial fuerte. El Presidente de la República
concentraba amplias atribuciones: nombraba intendentes y gobernadores,
intervenía en las elecciones y contaba con facultades extraordinarias en
situaciones de crisis. Diego Portales, aunque nunca ejerció la presidencia,
articuló la idea de un gobierno impersonal y obedecido, base del orden
portaliano.

Durante la segunda mitad del siglo, las reformas de 1871 a 1874 limitaron
progresivamente el poder presidencial: se prohibió la reelección inmediata,
se restringieron las facultades extraordinarias y se amplió el derecho de
sufragio. Este proceso de parlamentarización culminó en la guerra civil de
1891, tras la cual el Congreso se impuso sobre el Ejecutivo, inaugurando el
período parlamentario chileno.

El llamado régimen parlamentario chileno (1891-1925) no replicó el modelo
británico: careció de mecanismos como la disolución del parlamento, y la
rotativa ministerial produjo inestabilidad gubernamental crónica. Las
prácticas del período — interpelaciones frecuentes, leyes periódicas usadas
como herramienta de presión — configuraron un parlamentarismo de hecho más
que de derecho, cuya crisis abrió paso a la Constitución de 1925.
"""


# =============================================================================
# CLI
# =============================================================================
def _cmd_chunk(args: argparse.Namespace, cfg: ConfigTDAH) -> None:
    ruta = Path(args.archivo)
    texto = leer_documento(ruta)
    titulo = args.titulo or ruta.stem.replace("_", " ").replace("-", " ").title()
    chunker = MicroChunker(cfg)
    bloques = chunker.dividir(texto, titulo)

    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)
    for b in bloques:
        nombre = f"{_slug(titulo)} — Bloque {b.indice} de {b.total}.md"
        (salida / nombre).write_text(b.a_markdown(cfg), encoding="utf-8")

    print(chunker.resumen_plan(bloques))
    print(f"\n{len(bloques)} notas escritas en: {salida.resolve()}")
    print("Siguiente acción (2 min): abre el Bloque 1 y pon el temporizador.")


def _cmd_prompt(args: argparse.Namespace, cfg: ConfigTDAH) -> None:
    prompt = GeneradorPrompt.system_prompt(materia=args.materia)
    if args.payload:
        texto = leer_documento(Path(args.payload))
        print(json.dumps(GeneradorPrompt.payload_ejemplo(texto, args.materia),
                         ensure_ascii=False, indent=2))
    else:
        print(prompt)


def _cmd_vault(args: argparse.Namespace, cfg: ConfigTDAH) -> None:
    exportador = ExportadorObsidian(cfg)
    escritas = exportador.generar(Path(args.salida))
    print(f"Vault generado/actualizado en: {Path(args.salida).resolve()}")
    for p in escritas:
        print(f"  ✓ {p.relative_to(args.salida)}")
    print("\nSiguiente acción (2 min): abre la carpeta como vault en Obsidian "
          "e instala el plugin Dataview para activar el dashboard.")


def _cmd_demo(args: argparse.Namespace, cfg: ConfigTDAH) -> None:
    print("=" * 70)
    print("DEMO 1/3 — Chunking de texto de ejemplo (Historia Constitucional)")
    print("=" * 70)
    chunker = MicroChunker(cfg)
    bloques = chunker.dividir(TEXTO_DEMO, "Historia Constitucional de Chile")
    print(chunker.resumen_plan(bloques))
    print()
    print("=" * 70)
    print("DEMO 2/3 — Primeras líneas del System Prompt para el LLM")
    print("=" * 70)
    print("\n".join(GeneradorPrompt.system_prompt().splitlines()[:12]))
    print("    [... completo con: python extractor_tdah.py prompt]")
    print()
    print("=" * 70)
    print("DEMO 3/3 — Vault Obsidian")
    print("=" * 70)
    destino = Path(args.salida)
    escritas = ExportadorObsidian(cfg).generar(destino)
    print(f"{len(escritas)} archivos de vault escritos en {destino.resolve()}")


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        prog="extractor_tdah",
        description="Plantilla de Extracción de Conocimiento para TDAH "
                    "(micro-learning 15 min + prompt LLM + vault Obsidian).",
    )
    parser.add_argument("--config", default="config_tdah.json",
                        help="ruta al JSON de configuración (opcional)")
    sub = parser.add_subparsers(dest="comando", required=True)

    p_chunk = sub.add_parser("chunk", help="trocear un capítulo en bloques de 15 min")
    p_chunk.add_argument("archivo", help="ruta a .txt/.md/.pdf")
    p_chunk.add_argument("--titulo", default=None, help="título de la fuente")
    p_chunk.add_argument("--salida", default="bloques", help="carpeta de salida")
    p_chunk.set_defaults(fn=_cmd_chunk)

    p_prompt = sub.add_parser("prompt", help="imprimir el system prompt LLM")
    p_prompt.add_argument("--materia", default="Derecho e Historia")
    p_prompt.add_argument("--payload", default=None,
                          help="ruta a documento: imprime el payload JSON completo")
    p_prompt.set_defaults(fn=_cmd_prompt)

    p_vault = sub.add_parser("vault", help="generar el vault Obsidian")
    p_vault.add_argument("--salida", default="vault_tdah", help="carpeta del vault")
    p_vault.set_defaults(fn=_cmd_vault)

    p_demo = sub.add_parser("demo", help="ejecutar los 3 módulos con datos de ejemplo")
    p_demo.add_argument("--salida", default="vault_tdah", help="carpeta del vault demo")
    p_demo.set_defaults(fn=_cmd_demo)

    args = parser.parse_args(argv)
    cfg = ConfigTDAH.desde_json(Path(args.config)) if Path(args.config).exists() \
        else ConfigTDAH()
    args.fn(args, cfg)


if __name__ == "__main__":
    main()
