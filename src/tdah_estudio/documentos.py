"""Lectura de documentos de entrada (.txt/.md/.pdf) y texto de demostración.

El import de pypdf está protegido a propósito: el sistema NUNCA debe fallar
por una dependencia ausente con un traceback críptico. Para un usuario con
TDAH, un ImportError en el primer intento de uso es fricción suficiente
para abandonar la herramienta completa — la barrera de inicio es el punto
de fallo ejecutivo número uno en TDAH inatento. Por eso todo error de este
módulo es un ``ErrorDocumento`` con instrucciones de solución, no un
traceback.
"""

from __future__ import annotations

from pathlib import Path

try:
    from pypdf import PdfReader

    _PDF_DISPONIBLE = True
except ImportError:  # pragma: no cover - se simula con monkeypatch en tests
    _PDF_DISPONIBLE = False

# Un PDF con menos de 50 palabras extraíbles es casi seguro un escaneo sin
# capa de texto: mejor avisar YA que producir un único bloque vacío que el
# estudiante descubra al abrir la nota.
UMBRAL_PALABRAS_PDF = 50


class ErrorDocumento(RuntimeError):
    """Error de lectura con mensaje accionable (qué pasó + cómo arreglarlo)."""


def leer_documento(ruta: Path) -> str:
    """Devuelve el texto plano de un .txt/.md/.pdf.

    Todos los caminos de error lanzan ErrorDocumento con la solución
    incluida en el mensaje; la CLI lo muestra y sale con código 2.
    """
    if not ruta.exists():
        raise ErrorDocumento(
            f"No existe el archivo '{ruta}'. Revisa la ruta (¿estás en la "
            f"carpeta correcta?) y reintenta."
        )
    if ruta.suffix.lower() == ".pdf":
        return _leer_pdf(ruta)
    try:
        return ruta.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise ErrorDocumento(f"No se pudo leer '{ruta}': {exc}") from exc


def _leer_pdf(ruta: Path) -> str:
    if not _PDF_DISPONIBLE:
        raise ErrorDocumento(
            "Para leer PDF directamente instala el extra:  pip install 'tdah-estudio[pdf]'  "
            "(o  pip install pypdf ).\n"
            "Alternativa inmediata sin instalar nada: copia el texto del PDF "
            "a un archivo .txt y reintenta con ese archivo."
        )
    lector = PdfReader(str(ruta))
    texto = "\n\n".join(pagina.extract_text() or "" for pagina in lector.pages)
    if len(texto.split()) < UMBRAL_PALABRAS_PDF:
        raise ErrorDocumento(
            f"El PDF '{ruta.name}' casi no tiene capa de texto "
            f"({len(texto.split())} palabras extraídas): probablemente es un "
            f"documento escaneado. Pásalo por OCR antes de trocearlo."
        )
    return texto


# Texto de demostración: permite probar el sistema completo en 30 segundos
# sin buscar material propio (eliminar la fricción del primer uso).
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
