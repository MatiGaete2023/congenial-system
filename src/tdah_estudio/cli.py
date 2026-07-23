"""CLI: orquesta config + documentos + chunker + prompts + obsidian.

Diseño de la interfaz para TDAH:
- Cada subcomando termina imprimiendo la SIGUIENTE ACCIÓN concreta de
  menos de 2 minutos ("abre el Bloque 1 y pon el temporizador"): la
  transición entre herramienta y estudio es donde se pierde el impulso,
  así que la herramienta entrega el primer paso ya masticado.
- Los errores esperables (archivo inexistente, PDF escaneado, pypdf
  ausente) salen con código 2 y mensaje accionable, sin traceback: un
  traceback es ruido que castiga el intento de uso.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tdah_estudio import __version__
from tdah_estudio.chunker import MicroChunker
from tdah_estudio.config import ConfigTDAH, cargar_config
from tdah_estudio.documentos import TEXTO_DEMO, ErrorDocumento, leer_documento
from tdah_estudio.obsidian import (
    ExportadorObsidian,
    nombre_archivo_bloque,
    render_bloque,
)
from tdah_estudio.prompts import payload_api, system_prompt


def _cmd_chunk(args: argparse.Namespace, cfg: ConfigTDAH) -> int:
    ruta = Path(args.archivo)
    texto = leer_documento(ruta)
    titulo = args.titulo or ruta.stem.replace("_", " ").replace("-", " ").title()
    chunker = MicroChunker(cfg)
    bloques = chunker.dividir(texto, titulo)

    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)
    for b in bloques:
        (salida / nombre_archivo_bloque(b)).write_text(
            render_bloque(b, cfg), encoding="utf-8"
        )

    print(chunker.resumen_plan(bloques))
    print(f"\n{len(bloques)} notas escritas en: {salida.resolve()}")
    print("Siguiente acción (2 min): abre el Bloque 1 y pon el temporizador.")
    return 0


def _cmd_prompt(args: argparse.Namespace, cfg: ConfigTDAH) -> int:
    if args.payload:
        texto = leer_documento(Path(args.payload))
        print(json.dumps(payload_api(cfg, texto, args.materia), ensure_ascii=False, indent=2))
    else:
        print(system_prompt(materia=args.materia))
    return 0


def _cmd_vault(args: argparse.Namespace, cfg: ConfigTDAH) -> int:
    raiz = Path(args.salida)
    escritas = ExportadorObsidian(cfg).generar(raiz)
    print(f"Vault generado/actualizado en: {raiz.resolve()}")
    for p in escritas:
        print(f"  ✓ {p.relative_to(raiz)}")
    print(
        "\nSiguiente acción (2 min): abre la carpeta como vault en Obsidian "
        "e instala el plugin Dataview para activar el dashboard."
    )
    return 0


def _cmd_demo(args: argparse.Namespace, cfg: ConfigTDAH) -> int:
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
    print("\n".join(system_prompt().splitlines()[:12]))
    print("    [... completo con: tdah-estudio prompt]")
    print()
    print("=" * 70)
    print("DEMO 3/3 — Vault Obsidian")
    print("=" * 70)
    escritas = ExportadorObsidian(cfg).generar(Path(args.salida))
    print(f"{len(escritas)} archivos de vault escritos en {Path(args.salida).resolve()}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tdah-estudio",
        description="Sistema de Extracción de Conocimiento para TDAH "
        "(micro-learning 15 min + prompt LLM + vault Obsidian).",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--config",
        default="config_tdah.json",
        help="ruta al JSON de configuración (por defecto: ./config_tdah.json)",
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    p_chunk = sub.add_parser("chunk", help="trocear un capítulo en bloques de 15 min")
    p_chunk.add_argument("archivo", help="ruta a .txt/.md/.pdf")
    p_chunk.add_argument("--titulo", default=None, help="título de la fuente")
    p_chunk.add_argument("--salida", default="bloques", help="carpeta de salida")
    p_chunk.set_defaults(fn=_cmd_chunk)

    p_prompt = sub.add_parser("prompt", help="imprimir el system prompt LLM")
    p_prompt.add_argument("--materia", default="Derecho e Historia")
    p_prompt.add_argument(
        "--payload",
        default=None,
        help="ruta a documento: imprime el payload JSON completo para la API",
    )
    p_prompt.set_defaults(fn=_cmd_prompt)

    p_vault = sub.add_parser("vault", help="generar el vault Obsidian")
    p_vault.add_argument("--salida", default="vault_tdah", help="carpeta del vault")
    p_vault.set_defaults(fn=_cmd_vault)

    p_demo = sub.add_parser("demo", help="ejecutar los 3 módulos con datos de ejemplo")
    p_demo.add_argument("--salida", default="vault_tdah", help="carpeta del vault demo")
    p_demo.set_defaults(fn=_cmd_demo)

    args = parser.parse_args(argv)
    cfg = cargar_config(Path(args.config))
    try:
        resultado: int = args.fn(args, cfg)
        return resultado
    except (ErrorDocumento, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
