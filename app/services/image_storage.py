import mimetypes
import os
import uuid

from fastapi import HTTPException

from app.core.config import settings

_SUPABASE_AVAILABLE = True
try:
	from supabase import create_client
except Exception:
	_SUPABASE_AVAILABLE = False
	create_client = None

IMAGES_DIR = os.path.join(settings.MEDIA_DIR, "images")
_EXT_BY_CONTENT_TYPE = {
	"image/jpeg": "jpg",
	"image/png": "png",
	"image/webp": "webp",
	"image/gif": "gif",
}


def _infer_extension(original_filename: str | None, content_type: str | None) -> str:
	if content_type in _EXT_BY_CONTENT_TYPE:
		return _EXT_BY_CONTENT_TYPE[content_type]

	raw_name = original_filename or "image"
	if "." in raw_name:
		ext = raw_name.rsplit(".", 1)[-1].lower()
		if ext in {"jpg", "jpeg", "png", "webp", "gif"}:
			return "jpg" if ext == "jpeg" else ext
	return "jpg"


def _save_local_image(content: bytes, extension: str) -> str:
	filename = f"{uuid.uuid4().hex}.{extension}"
	os.makedirs(IMAGES_DIR, exist_ok=True)
	with open(os.path.join(IMAGES_DIR, filename), "wb") as local_file:
		local_file.write(content)
	return f"/media/images/{filename}"


def _build_supabase_path(extension: str) -> str:
	base_prefix = (settings.SUPABASE_PRODUCTS_PREFIX or "products").strip("/")
	if not base_prefix:
		base_prefix = "products"
	return f"{base_prefix}/{uuid.uuid4().hex}.{extension}"


def upload_product_image_to_supabase(
	*, content: bytes, original_filename: str | None, content_type: str | None
) -> str:
	if not settings.SUPABASE_STORAGE_ENABLED:
		raise RuntimeError("Supabase Storage no está configurado")
	if not _SUPABASE_AVAILABLE or create_client is None:
		raise RuntimeError("Paquete supabase no instalado")

	extension = _infer_extension(original_filename, content_type)
	storage_path = _build_supabase_path(extension)
	mime_type = content_type or mimetypes.guess_type(f"x.{extension}")[0] or "application/octet-stream"

	client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
	client.storage.from_(settings.SUPABASE_BUCKET).upload(
		path=storage_path,
		file=content,
		file_options={"content-type": mime_type, "upsert": "false"},
	)
	return client.storage.from_(settings.SUPABASE_BUCKET).get_public_url(storage_path)


def save_product_image(*, content: bytes, original_filename: str | None, content_type: str | None) -> str:
	try:
		if settings.SUPABASE_STORAGE_ENABLED:
			return upload_product_image_to_supabase(
				content=content,
				original_filename=original_filename,
				content_type=content_type,
			)
	except Exception as ex:
		if settings.SUPABASE_STORAGE_STRICT:
			raise HTTPException(500, detail=f"No se pudo subir a Supabase Storage: {ex}") from ex

	return _save_local_image(content, _infer_extension(original_filename, content_type))
