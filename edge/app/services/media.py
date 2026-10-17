"""Photo resize / EXIF strip and audio temp storage under DATA_DIR."""

from __future__ import annotations

import io
from pathlib import Path

from beacon_contract import new_id
from PIL import Image

from app.config import get_settings

_MAX_EDGE = 1280
_JPEG_QUALITY = 70


def media_root() -> Path:
    root = Path(get_settings().data_dir) / "media"
    root.mkdir(parents=True, exist_ok=True)
    return root


def save_photo(data: bytes) -> tuple[str, Path]:
    """Resize to max 1280 px, JPEG q70, strip EXIF. Returns (media_id, path)."""
    media_id = new_id()
    img = Image.open(io.BytesIO(data))
    img = img.convert("RGB")
    w, h = img.size
    scale = min(1.0, _MAX_EDGE / max(w, h))
    if scale < 1.0:
        img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
    path = media_root() / f"{media_id}.jpg"
    # Saving a new JPEG omits EXIF from the source.
    img.save(path, format="JPEG", quality=_JPEG_QUALITY, optimize=True)
    return media_id, path


def save_audio(data: bytes, suffix: str = ".webm") -> tuple[str, Path]:
    media_id = new_id()
    path = media_root() / f"{media_id}{suffix}"
    path.write_bytes(data)
    return media_id, path


def delete_path(path: str | Path | None) -> None:
    if not path:
        return
    p = Path(path)
    if p.is_file():
        p.unlink(missing_ok=True)
