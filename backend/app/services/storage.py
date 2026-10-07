import hashlib
from dataclasses import dataclass
from pathlib import Path

from app.domain.filenames import sanitize_storage_name
from app.errors import IngestionError
from app.messages import text

ORIGINAL_VERSION_DIR = "v0"


@dataclass(frozen=True)
class StoredFile:
    relative_path: str
    sha256: str
    byte_size: int


class FileStore:
    """Writes original bytes once. Version 0 is never opened for overwrite."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def write_new(self, document_id: str, filename: str, content: bytes) -> StoredFile:
        safe_name = sanitize_storage_name(filename)
        relative = Path("documents") / document_id / ORIGINAL_VERSION_DIR / safe_name
        destination = self._resolve(relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            with destination.open("xb") as handle:
                handle.write(content)
        except FileExistsError as exc:
            raise IngestionError("storage_conflict", text("storage_conflict")) from exc
        return StoredFile(
            relative_path=relative.as_posix(),
            sha256=hashlib.sha256(content).hexdigest(),
            byte_size=len(content),
        )

    def read(self, relative_path: str) -> bytes:
        return self._resolve(Path(relative_path)).read_bytes()

    def discard(self, relative_path: str) -> None:
        path = self._resolve(Path(relative_path))
        path.unlink(missing_ok=True)
        current = path.parent
        while current != self.root:
            try:
                current.rmdir()
            except OSError:
                return
            current = current.parent

    def _resolve(self, relative: Path) -> Path:
        if relative.is_absolute() or ".." in relative.parts:
            raise IngestionError("invalid_storage_path", text("invalid_storage_path"))
        destination = (self.root / relative).resolve()
        if not destination.is_relative_to(self.root):
            raise IngestionError("invalid_storage_path", text("invalid_storage_path"))
        return destination
