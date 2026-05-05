"""
Pobla la base con datos de prueba: usuarios/roles mínimos, catálogo, insumos e inventario.

Ejecutar desde la raíz del proyecto: ``python scripts/seed.py``
(con ``DATABASE_URL`` / ``.env`` apuntando a la BD).
"""

from .runner import run_all

__all__ = ["run_all"]
