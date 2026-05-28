#!/usr/bin/env python3
"""Actualiza la contraseña del admin demo de forma segura.

Uso:
  NEW_ADMIN_PASSWORD=MiClaveSegura123 python scripts/update_admin_password.py
o ejecuta sin variable y te pedirá la contraseña por prompt.

No almacenes la contraseña en el repo. Ejecuta este script en el entorno del servidor.
"""

import getpass
import os
import sys

from sqlmodel import Session, select

from app.core.database import engine
from app.core.security import hash_password
from app.models.security import SystemUser


def main():
    email = os.getenv("ADMIN_EMAIL", "admin@example.com")
    new_password = os.getenv("NEW_ADMIN_PASSWORD")
    if not new_password:
        try:
            new_password = getpass.getpass("Nueva contraseña para admin@example.com: ")
        except Exception:
            print(
                "No se pudo leer la contraseña desde prompt. " "Usa la variable NEW_ADMIN_PASSWORD."
            )
            sys.exit(1)

    if not new_password:
        print("Contraseña vacía. Abortando.")
        sys.exit(1)

    with Session(engine) as session:
        user = session.exec(select(SystemUser).where(SystemUser.email == email)).first()
        if not user:
            print(
                f"Usuario {email} no encontrado. Asegúrate de que los seeders "
                "hayan corrido o crea el usuario."
            )
            sys.exit(1)

        user.password_hash = hash_password(new_password)
        session.add(user)
        session.commit()
        print(f"Contraseña de {email} actualizada correctamente.")


if __name__ == "__main__":
    main()
