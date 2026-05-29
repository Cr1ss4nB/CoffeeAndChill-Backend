"""Entry point temporal para poblar la base con datos de demo amplios.

Ejecutar desde la raíz del backend:
    python scripts/seed_full_demo_temp.py
"""

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from seeders.full_demo import run_full_demo  # noqa: E402


if __name__ == "__main__":
    run_full_demo()