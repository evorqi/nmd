import re
from pathlib import Path

from app.errors import IngestionError
from app.messages import text

_STEM_REPLACEMENTS = re.compile(r"[^0-9A-Za-z\u0600-\u06FF\u200c ._-]")


def display_filename(filename: str) -> str:
    name = filename.replace("\\", "/").split("/")[-1].strip()
    name = re.sub(r"[\x00-\x1f]", "", name)
    if name in {"", ".", ".."}:
        raise IngestionError("invalid_filename", text("invalid_filename"))
    return name[:180]


def extension_of(filename: str) -> str:
    try:
        name = display_filename(filename)
    except IngestionError:
        return ""
    return Path(name).suffix.lower().removeprefix(".")


def sanitize_storage_name(filename: str) -> str:
    name = display_filename(filename)
    extension = re.sub(r"[^0-9a-z.]", "", Path(name).suffix.lower())[:12]
    stem = _STEM_REPLACEMENTS.sub("_", Path(name).stem)
    stem = re.sub(r"_+", "_", stem).strip(" ._")
    if not stem:
        stem = "upload"
    return f"{stem[:80]}{extension}"
