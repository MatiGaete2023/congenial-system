"""Permite `python -m tdah_estudio` además del script `tdah-estudio`."""

import sys

from tdah_estudio.cli import main

if __name__ == "__main__":
    sys.exit(main())
