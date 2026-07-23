"""Configuración calibrada neurocognitivamente, con carga que AVISA.

Regla de diseño (restricción 5 del proceso v2): degradar a valores por
defecto está permitido, degradar EN SILENCIO no. Un usuario con TDAH que
escribe ``minutos_por_bloqe`` (typo) en el JSON creería haber configurado
20 minutos mientras el sistema usa 15: esa discrepancia invisible erosiona
la confianza en el sistema, y la confianza es el pegamento que sostiene
cualquier rutina de estudio TDAH. Cada clave desconocida y cada valor fuera
de rango produce una línea en stderr.

FUNDAMENTO NEUROCIENTÍFICO DE LOS VALORES POR DEFECTO
-----------------------------------------------------
* ppm_lectura_densa = 110: un adulto lee prosa general a 200-250 palabras/min;
  texto jurídico denso baja a ~150 por carga sintáctica, y el TDAH inatento
  descuenta otro ~25-30% por relecturas involuntarias (la atención sostenida
  decae en ondas de 8-12 minutos y obliga a releer). Se prefiere subestimar:
  terminar antes de tiempo genera dopamina; desbordar genera frustración.
* minutos_por_bloque = 15: la atención sostenida sin estímulo externo en TDAH
  colapsa de forma medible entre los 10 y los 20 minutos; 15 está en la
  ventana segura Y divide la hora en 4 (menos aritmética = menos carga
  ejecutiva al planificar).
* minutos_lectura_efectiva = 11: los 4 minutos restantes viven DENTRO del
  bloque (2 de recuperación activa + 2 de recompensa). Si la recompensa
  quedara fuera del bloque, el descuento hiperbólico del refuerzo demorado
  — más pronunciado en TDAH — la anularía como motivador.
* max_ideas_por_bloque = 5: memoria de trabajo = 4±1 chunks (Cowan, 2001);
  en TDAH conviene asumir el extremo bajo del rango.
* bloques_por_sesion_max = 4: tras ~60 minutos la capacidad de inhibir
  distractores del córtex prefrontal dorsolateral se agota físicamente;
  el sistema se niega a planificar heroicidades.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any

# Rangos plausibles por campo: fuera de esto el valor es casi seguro un error
# de tipeo (p. ej. 1100 ppm) y se sustituye por el defecto, avisando.
_RANGOS: dict[str, tuple[int, int]] = {
    "ppm_lectura_densa": (40, 400),
    "minutos_por_bloque": (5, 60),
    "minutos_lectura_efectiva": (1, 58),
    "max_ideas_por_bloque": (1, 9),
    "bloques_por_sesion_max": (1, 8),
    "minutos_pausa_corta": (1, 15),
    "minutos_descanso_largo": (5, 90),
}


def _avisar(mensaje: str) -> None:
    """Canal único de avisos de configuración (stderr, prefijo estable)."""
    print(f"[config_tdah] {mensaje}", file=sys.stderr)


@dataclass
class ConfigTDAH:
    """Parámetros del sistema. Ver justificación de valores en el módulo."""

    ppm_lectura_densa: int = 110
    minutos_por_bloque: int = 15
    minutos_lectura_efectiva: int = 11
    max_ideas_por_bloque: int = 5
    bloques_por_sesion_max: int = 4
    minutos_pausa_corta: int = 2
    minutos_descanso_largo: int = 20
    # El ID de modelo vive aquí y NO hardcodeado en prompts.py
    # (restricción 5): cambiar de modelo es editar una línea de JSON.
    modelo_llm: str = "claude-sonnet-5"

    @property
    def palabras_por_bloque(self) -> int:
        """Palabras que caben en la ventana de lectura efectiva de un bloque.

        110 ppm x 11 min = 1210 palabras: una cantidad FINITA y VISIBLE.
        El estudiante nunca abre un bloque sin saber cuánto le queda
        (antídoto directo contra la ceguera temporal del TDAH).
        """
        return self.ppm_lectura_densa * self.minutos_lectura_efectiva

    # ------------------------------------------------------------------ #
    @classmethod
    def desde_json(cls, ruta: Path) -> ConfigTDAH:
        """Carga la configuración avisando de TODO lo que descarta.

        Convenciones del archivo:
        - Claves que empiezan con ``$`` son comentarios y se ignoran en
          silencio (JSON no tiene comentarios nativos).
        - Clave desconocida -> aviso por stderr + descarte.
        - Valor fuera de rango o de tipo incorrecto -> aviso + defecto.
        - JSON ilegible -> aviso + configuración completa por defecto.
        """
        try:
            crudo: dict[str, Any] = json.loads(ruta.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            _avisar(f"no se pudo leer {ruta} ({exc}); uso TODOS los valores por defecto")
            return cls()
        if not isinstance(crudo, dict):
            _avisar(f"{ruta} no contiene un objeto JSON; uso valores por defecto")
            return cls()

        nombres_validos = {f.name for f in fields(cls)}
        defectos = cls()
        aceptados: dict[str, Any] = {}

        for clave, valor in crudo.items():
            if clave.startswith("$"):
                continue  # comentario documentado, silencio deliberado
            if clave not in nombres_validos:
                _avisar(f"clave desconocida '{clave}' ignorada "
                        f"(¿typo? campos válidos: {sorted(nombres_validos)})")
                continue
            if clave == "modelo_llm":
                if isinstance(valor, str) and valor.strip():
                    aceptados[clave] = valor.strip()
                else:
                    _avisar(f"'modelo_llm' debe ser texto no vacío; "
                            f"uso '{defectos.modelo_llm}'")
                continue
            minimo, maximo = _RANGOS[clave]
            if not isinstance(valor, int) or isinstance(valor, bool):
                _avisar(f"'{clave}' debe ser entero (recibí {valor!r}); "
                        f"uso {getattr(defectos, clave)}")
                continue
            if not (minimo <= valor <= maximo):
                _avisar(f"'{clave}'={valor} fuera de rango [{minimo}, {maximo}]; "
                        f"uso {getattr(defectos, clave)}")
                continue
            aceptados[clave] = valor

        cfg = cls(**aceptados)
        return cfg._coherencia_cruzada()

    # ------------------------------------------------------------------ #
    def _coherencia_cruzada(self) -> ConfigTDAH:
        """Repara relaciones imposibles ENTRE campos, avisando.

        La lectura efectiva + recuperación (2 min fijos) + pausa corta deben
        caber dentro del bloque; si no caben, el contrato temporal del bloque
        sería mentira, y un contrato temporal roto es exactamente lo que este
        sistema existe para evitar.
        """
        minutos_fijos = 2 + self.minutos_pausa_corta  # recuperación + recompensa
        if self.minutos_lectura_efectiva + minutos_fijos > self.minutos_por_bloque:
            corregido = max(1, self.minutos_por_bloque - minutos_fijos)
            _avisar(
                f"minutos_lectura_efectiva={self.minutos_lectura_efectiva} no cabe en "
                f"un bloque de {self.minutos_por_bloque} min con {minutos_fijos} min "
                f"fijos de cierre; lo ajusto a {corregido}"
            )
            self.minutos_lectura_efectiva = corregido
        return self


def cargar_config(ruta: Path | None = None) -> ConfigTDAH:
    """Punto de entrada único: archivo si existe, defaults si no.

    La ausencia del archivo NO es un error ni produce aviso: el sistema
    debe funcionar de fábrica sin ningún paso de configuración previo
    (toda fricción de arranque es una oportunidad de abandono).
    """
    if ruta is not None and ruta.exists():
        return ConfigTDAH.desde_json(ruta)
    return ConfigTDAH()
