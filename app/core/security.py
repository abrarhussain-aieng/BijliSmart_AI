"""Upload validation: extension, size and file signature checks."""
import os
import re

from app.core.config import settings
from app.utils.validators import FileValidationError

ALLOWED_EXTENSIONS = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
}


def detect_mime(content: bytes) -> str | None:
    """Identify the real file type from its magic bytes."""
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    if content.startswith(b"%PDF"):
        return "application/pdf"
    return None


def sanitize_filename(filename: str) -> str:
    """Return a safe base filename."""
    name = os.path.basename(filename or "bill")
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)[:120] or "bill"


def validate_upload(filename: str, content: bytes) -> str:
    """Validate an uploaded bill and return its verified MIME type."""
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise FileValidationError("Unsupported file type. Upload a PNG, JPG, JPEG, WEBP or PDF file.")
    if not content:
        raise FileValidationError("The uploaded file is empty.")
    if len(content) > settings.max_upload_bytes:
        raise FileValidationError(f"File is too large. The limit is {settings.max_upload_mb} MB.")
    mime = detect_mime(content)
    if mime is None or mime != ALLOWED_EXTENSIONS[ext]:
        raise FileValidationError("The file content does not match its extension or is unreadable.")
    return mime
