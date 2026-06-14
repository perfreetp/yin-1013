import os
import hashlib
import aiofiles
from typing import Optional
from pathlib import Path
from datetime import datetime
from app.config import settings
from app.core.logger import logger


def get_storage_path(sub_path: str = "") -> str:
    base_path = os.path.abspath(settings.STORAGE_PATH)
    full_path = os.path.join(base_path, sub_path)
    os.makedirs(full_path, exist_ok=True)
    return full_path


def generate_unique_filename(original_name: str, prefix: str = "") -> str:
    ext = os.path.splitext(original_name)[1] or ""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    if prefix:
        return f"{prefix}_{timestamp}{ext}"
    return f"{timestamp}{ext}"


def get_file_hash(file_path: str, algorithm: str = "sha256") -> Optional[str]:
    if not os.path.exists(file_path):
        return None

    hash_obj = hashlib.new(algorithm)
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


async def save_upload_file(file_content: bytes, file_name: str, sub_path: str = "uploads") -> dict:
    storage_dir = get_storage_path(sub_path)
    file_path = os.path.join(storage_dir, file_name)

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(file_content)

    file_hash = get_file_hash(file_path)
    file_size = os.path.getsize(file_path)

    relative_path = os.path.join(sub_path, file_name)

    return {
        "file_name": file_name,
        "file_path": relative_path,
        "file_url": f"/{relative_path}",
        "file_size": file_size,
        "file_hash": file_hash
    }


def validate_file_type(content_type: str, allowed_types: list) -> bool:
    return content_type.lower() in [t.lower() for t in allowed_types]


def validate_file_size(file_size: int, max_size: int = None) -> bool:
    if max_size is None:
        max_size = settings.MAX_FILE_SIZE
    return file_size <= max_size


def format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
