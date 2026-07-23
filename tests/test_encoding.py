"""Restricción 6 del proceso: todo archivo fuente es UTF-8 válido y sin U+FFFD.

Este test existe porque en la iteración 1 un carácter de reemplazo (mojibake)
llegó a un archivo escrito de un solo golpe y hubo que parchearlo después.
Un assert de dos líneas convierte ese error en imposible de repetir.
"""

from __future__ import annotations

from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
EXTENSIONES = {".py", ".md", ".json", ".toml", ".yml", ".yaml"}
DIRECTORIOS_EXCLUIDOS = {".git", "__pycache__", ".pytest_cache", ".hypothesis",
                         ".mypy_cache", ".ruff_cache", "vault_tdah", "bloques"}


def _archivos_fuente() -> list[Path]:
    encontrados = []
    for ruta in RAIZ.rglob("*"):
        if ruta.suffix not in EXTENSIONES or not ruta.is_file():
            continue
        if any(parte in DIRECTORIOS_EXCLUIDOS for parte in ruta.parts):
            continue
        encontrados.append(ruta)
    return encontrados


def test_hay_archivos_que_revisar() -> None:
    assert len(_archivos_fuente()) >= 5


def test_todo_archivo_fuente_es_utf8_sin_reemplazos() -> None:
    infractores = []
    for ruta in _archivos_fuente():
        try:
            contenido = ruta.read_bytes().decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            infractores.append(f"{ruta}: no es UTF-8 válido ({exc})")
            continue
        if "\ufffd" in contenido:
            infractores.append(f"{ruta}: contiene U+FFFD (caracter de reemplazo)")
    assert not infractores, "\n".join(infractores)
