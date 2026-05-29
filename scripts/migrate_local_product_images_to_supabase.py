#!/usr/bin/env python3
"""Migra imágenes locales de productos a Supabase Storage.

Convierte Product.image_url desde rutas locales tipo /media/images/xxx.jpg
hacia URLs públicas de Supabase Storage.

Uso:
  python scripts/migrate_local_product_images_to_supabase.py

Opcionales:
  DRY_RUN=true python scripts/migrate_local_product_images_to_supabase.py
"""

import mimetypes
import os
import sys

from sqlmodel import Session, select

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from app.core.config import settings  # noqa: E402
from app.core.database import engine  # noqa: E402
from app.models.catalog import Product  # noqa: E402
from app.services.image_storage import upload_product_image_to_supabase  # noqa: E402


def _to_bool(raw: str | None) -> bool:
    return (raw or "").strip().lower() in {"1", "true", "yes", "on"}


def _local_path_from_media_url(image_url: str) -> str | None:
    if not image_url.startswith("/media/"):
        return None
    rel_path = image_url[len("/media/") :]
    return os.path.join(settings.MEDIA_DIR, rel_path.replace("/", os.sep))


def main() -> int:
    if not settings.SUPABASE_STORAGE_ENABLED:
        print("Supabase Storage no está configurado. Revisa SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY y SUPABASE_BUCKET.")
        return 1

    dry_run = _to_bool(os.getenv("DRY_RUN"))

    migrated = 0
    skipped = 0
    missing = 0
    failed = 0

    with Session(engine) as session:
        products = session.exec(select(Product).where(Product.image_url.is_not(None))).all()

        for product in products:
            current_url = product.image_url or ""
            local_path = _local_path_from_media_url(current_url)

            if not local_path:
                skipped += 1
                continue

            if not os.path.exists(local_path):
                print(f"[MISSING] Producto #{product.product_id}: no existe {local_path}")
                missing += 1
                continue

            try:
                with open(local_path, "rb") as image_file:
                    content = image_file.read()

                mime_type = mimetypes.guess_type(local_path)[0] or "application/octet-stream"
                new_url = upload_product_image_to_supabase(
                    content=content,
                    original_filename=os.path.basename(local_path),
                    content_type=mime_type,
                )

                if dry_run:
                    print(f"[DRY_RUN] Producto #{product.product_id}: {current_url} -> {new_url}")
                    migrated += 1
                    continue

                product.image_url = new_url
                session.add(product)
                migrated += 1
                print(f"[OK] Producto #{product.product_id}: {new_url}")
            except Exception as ex:
                failed += 1
                print(f"[ERROR] Producto #{product.product_id}: {ex}")

        if not dry_run:
            session.commit()

    print("\nResumen:")
    print(f"  Migradas: {migrated}")
    print(f"  Omitidas (ya externas): {skipped}")
    print(f"  Faltantes en disco: {missing}")
    print(f"  Fallidas: {failed}")
    print(f"  Modo: {'DRY_RUN' if dry_run else 'APLICADO'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
