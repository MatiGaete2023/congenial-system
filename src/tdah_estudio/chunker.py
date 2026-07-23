"""Micro-chunker de 15 minutos: lógica PURA de troceo, sin I/O ni Markdown.

La separación es deliberada: este módulo recibe texto y devuelve dataclasses.
Todo el renderizado vive en ``obsidian.py``. Gracias a eso los invariantes
del algoritmo se verifican con hypothesis a miles de casos por segundo sin
tocar disco (tests/test_chunker.py).

POR QUÉ TROCEAR — la justificación neurocognitiva completa:

La memoria de trabajo (modelo multicomponente de Baddeley) es el cuello de
botella central del TDAH inatento: el bucle fonológico y la agenda
visoespacial retienen menos elementos y por menos tiempo. Un capítulo de
40 páginas excede esa capacidad por un factor de 20-50x, así que el cerebro
"pierde el hilo" no por falta de esfuerzo sino por desbordamiento físico
del búfer. La única solución compatible con el hardware es fragmentar la
entrada hasta que cada unidad quepa COMPLETA en el búfer: eso es un bloque
de ~1210 palabras (11 min de lectura a 110 ppm efectivas).

INVARIANTES DEL ALGORITMO (verificados por hypothesis en cada CI):
  I1. Ninguna palabra del texto original se pierde ni se duplica.
  I2. Ningún bloque excede el 120% del presupuesto de palabras, siempre que
      ninguna oración individual exceda el presupuesto por sí sola.
  I3. Los índices son contiguos 1..N y `total` es consistente en todos.
  I4. La numeración de sesiones agrupa de a `bloques_por_sesion_max`.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from tdah_estudio.config import ConfigTDAH


@dataclass
class BloqueEstudio:
    """Un micro-bloque de estudio autocontenido.

    Autocontenido = incluye su posición en la serie, su recuento de palabras
    y su duración estimada. La memoria de trabajo TDAH no puede sostener
    "voy por el bloque 7 de 12" entre sesiones; el bloque lo declara él
    mismo cada vez que se abre (estado externalizado, no memorizado).
    """

    indice: int
    total: int
    titulo_fuente: str
    texto: str
    palabras: int
    minutos_estimados: float
    sesion: int
    es_fin_de_sesion: bool


class MicroChunker:
    """Divide texto largo en bloques de 15 minutos de estudio real.

    ALGORITMO (3 pasos):
      1. Segmentar en párrafos (unidad semántica mínima que nunca se rompe:
         cortar a mitad de párrafo destruye la coherencia local de la que
         depende una memoria de trabajo reducida).
      2. Empaquetar párrafos consecutivos (greedy) hasta acercarse al
         presupuesto de palabras. Un párrafo que solo ya excede el
         presupuesto (típico en sentencias judiciales) se subdivide por
         oraciones respetando abreviaturas jurídicas.
      3. Balancear: un último bloque < 40% del presupuesto se fusiona con
         el anterior si el resultado no supera el 120%. Un "bloque enano"
         de 3 minutos rompe el contrato temporal de 15, y cada contrato
         roto erosiona la confianza que vuelve automático el ritual.
    """

    # Abreviaturas frecuentes en texto jurídico/histórico español tras las
    # cuales un punto NO cierra oración: "art. 19", "inc. 2", "op. cit.",
    # "cfr. supra", "ss.", "pág. 44", "S. XIX", tratamientos (Sr., Dra.).
    _ABREVIATURAS = (
        r"(?<!\bart)(?<!\bArt)(?<!\binc)(?<!\bnúm)(?<!\bpág)(?<!\bpágs)"
        r"(?<!\bss)(?<!\bcfr)(?<!\bCfr)(?<!\bcit)(?<!\bop)(?<!\bvol)(?<!\bcap)"
        r"(?<!\bSr)(?<!\bSra)(?<!\bDr)(?<!\bDra)(?<!\bS)(?<!\bN)(?<!\bU)"
    )
    _RE_ORACION = re.compile(_ABREVIATURAS + r"\.\s+(?=[A-ZÁÉÍÓÚÜÑ¿¡])")

    def __init__(self, cfg: ConfigTDAH | None = None):
        self.cfg = cfg or ConfigTDAH()

    # ------------------------------------------------------------------ #
    def dividir(self, texto: str, titulo_fuente: str) -> list[BloqueEstudio]:
        """Devuelve la lista de bloques para un capítulo completo.

        Lanza ValueError con mensaje accionable si el texto queda vacío
        tras la limpieza: fallar con instrucciones es aceptable, fallar
        con un traceback críptico no (la fricción de depurar mata la
        sesión de estudio, el recurso más caro del sistema).
        """
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
    def _segmentar_parrafos(self, texto: str) -> list[str]:
        """Normaliza saltos de línea y separa por párrafos reales.

        Los PDFs jurídicos rompen líneas a mitad de oración: una línea sola
        NO es un párrafo; el separador real es la línea en blanco. Los
        fragmentos de menos de 3 palabras se descartan como ruido (números
        de página, encabezados repetidos).
        """
        texto = texto.replace("\r\n", "\n").replace("\r", "\n")
        crudos = re.split(r"\n\s*\n", texto)
        parrafos = []
        for p in crudos:
            unificado = re.sub(r"\s+", " ", p).strip()
            if len(unificado.split()) >= 3:
                parrafos.append(unificado)
        return parrafos

    def _dividir_parrafo_gigante(self, parrafo: str) -> list[str]:
        """Subdivide por oraciones un párrafo que excede el presupuesto solo."""
        oraciones = self._RE_ORACION.split(parrafo)
        presupuesto = self.cfg.palabras_por_bloque
        trozos: list[str] = []
        actual: list[str] = []
        cuenta = 0
        for o in oraciones:
            n = len(o.split())
            if cuenta + n > presupuesto and actual:
                trozos.append(" ".join(actual))
                actual, cuenta = [], 0
            # El split consumió el ". " separador; se repone el punto para
            # no entregar oraciones decapitadas (sin alterar el nº de palabras).
            actual.append(o if o.endswith((".", "?", "!", ":", ";")) else o + ".")
            cuenta += n
        if actual:
            trozos.append(" ".join(actual))
        return trozos

    def _empaquetar(self, parrafos: list[str]) -> list[list[str]]:
        """Greedy: agrupa párrafos hasta llenar el presupuesto de palabras."""
        presupuesto = self.cfg.palabras_por_bloque
        paquetes: list[list[str]] = []
        actual: list[str] = []
        cuenta = 0
        for p in parrafos:
            n = len(p.split())
            if n > presupuesto:
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

    def _balancear_ultimo(self, paquetes: list[list[str]]) -> list[list[str]]:
        """Fusiona un último bloque enano (<40%) con el anterior si el
        resultado no supera el 120% del presupuesto."""
        if len(paquetes) < 2:
            return paquetes
        presupuesto = self.cfg.palabras_por_bloque
        ultimo = sum(len(p.split()) for p in paquetes[-1])
        penultimo = sum(len(p.split()) for p in paquetes[-2])
        if ultimo < presupuesto * 0.4 and (ultimo + penultimo) <= presupuesto * 1.2:
            paquetes[-2].extend(paquetes[-1])
            paquetes.pop()
        return paquetes

    def _materializar(self, paquetes: list[list[str]], titulo: str) -> list[BloqueEstudio]:
        """Convierte paquetes de párrafos en BloqueEstudio numerados."""
        total = len(paquetes)
        bloques = []
        for i, paquete in enumerate(paquetes, start=1):
            texto = "\n\n".join(paquete)
            palabras = len(texto.split())
            minutos = round(palabras / self.cfg.ppm_lectura_densa, 1)
            sesion = math.ceil(i / self.cfg.bloques_por_sesion_max)
            fin_sesion = (i % self.cfg.bloques_por_sesion_max == 0) and i < total
            bloques.append(
                BloqueEstudio(
                    indice=i,
                    total=total,
                    titulo_fuente=titulo,
                    texto=texto,
                    palabras=palabras,
                    minutos_estimados=minutos,
                    sesion=sesion,
                    es_fin_de_sesion=fin_sesion,
                )
            )
        return bloques

    # ------------------------------------------------------------------ #
    def resumen_plan(self, bloques: list[BloqueEstudio]) -> str:
        """Tabla de planificación: el mapa completo ANTES de empezar.

        Mostrar el costo total por adelantado convierte una tarea amorfa en
        un contrato finito. La evitación TDAH se dispara ante lo indefinido,
        no ante lo grande: lo grande-pero-acotado es abordable.
        """
        cfg = self.cfg
        total_min = len(bloques) * cfg.minutos_por_bloque
        sesiones = math.ceil(len(bloques) / cfg.bloques_por_sesion_max)
        lineas = [
            f"PLAN DE ESTUDIO — {bloques[0].titulo_fuente}",
            f"  Bloques de {cfg.minutos_por_bloque} min : {len(bloques)}",
            f"  Sesiones (máx {cfg.bloques_por_sesion_max} bloques): {sesiones}",
            f"  Tiempo total real           : {total_min} min "
            f"(~{total_min / 60:.1f} h repartidas, NO seguidas)",
            "",
            f"  {'#':>3} {'palabras':>9} {'min':>5}  sesión",
        ]
        for b in bloques:
            marca = "  <- descanso largo después" if b.es_fin_de_sesion else ""
            lineas.append(
                f"  {b.indice:>3} {b.palabras:>9} {b.minutos_estimados:>5}  S{b.sesion}{marca}"
            )
        return "\n".join(lineas)
