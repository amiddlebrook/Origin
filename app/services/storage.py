import os
import uuid
from typing import Tuple
from fastapi import UploadFile
from app.core.config import settings


def ensure_dirs() -> None:
    os.makedirs(settings.MEDIA_UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.ARTIFACTS_DIR, exist_ok=True)


def save_upload(file: UploadFile, subdir: str = "audio") -> Tuple[str, str]:
    """Save an uploaded file to MEDIA_UPLOAD_DIR/subdir and return (abs_path, rel_path)."""
    ensure_dirs()
    target_dir = os.path.join(settings.MEDIA_UPLOAD_DIR, subdir)
    os.makedirs(target_dir, exist_ok=True)
    ext = os.path.splitext(file.filename or "upload.bin")[1]
    fname = f"{uuid.uuid4().hex}{ext}"
    abs_path = os.path.join(target_dir, fname)
    # Persist to disk
    with open(abs_path, "wb") as out:
        out.write(file.file.read())
    # Build a project-relative path (for returning via API)
    rel_path = os.path.relpath(abs_path, start=".")
    return abs_path, rel_path
