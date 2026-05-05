"""
Punto de entrada para correr los seeders. Añade la raíz del repo a sys.path.
"""

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from seeders import run_all  # noqa: E402

if __name__ == "__main__":
    run_all()
