"""File-type registry.

Version 1 enables spreadsheet parsers only. Later file kinds are registered
and disabled so a new adapter can be added without a second upload path.
"""

from dataclasses import dataclass

from app.domain.filenames import extension_of
from app.errors import IngestionError
from app.messages import text


@dataclass(frozen=True)
class FileTypeSpec:
    extension: str
    label: str
    kind: str
    enabled: bool
    parser_key: str | None


class FileTypeRegistry:
    def __init__(self, specs: tuple[FileTypeSpec, ...]) -> None:
        self._by_extension = {spec.extension: spec for spec in specs}

    def register(self, spec: FileTypeSpec) -> None:
        self._by_extension[spec.extension] = spec

    def get(self, extension: str) -> FileTypeSpec | None:
        return self._by_extension.get(extension.lower().lstrip("."))

    def list_types(self) -> tuple[FileTypeSpec, ...]:
        return tuple(self._by_extension.values())

    def resolve(self, filename: str) -> FileTypeSpec:
        extension = extension_of(filename)
        spec = self.get(extension)
        if spec is None:
            raise IngestionError("unsupported_file_type", text("unsupported_file_type"))
        if not spec.enabled or spec.parser_key is None:
            raise IngestionError("file_type_not_enabled", text("file_type_not_enabled"))
        return spec


def build_default_registry() -> FileTypeRegistry:
    return FileTypeRegistry(_DEFAULT_SPECS)


_DEFAULT_SPECS: tuple[FileTypeSpec, ...] = (
    FileTypeSpec("xlsx", "اکسل", "spreadsheet", True, "xlsx"),
    FileTypeSpec("xls", "اکسل قدیمی", "spreadsheet", True, "xls"),
    FileTypeSpec("csv", "CSV", "spreadsheet", True, "csv"),
    FileTypeSpec("pdf", "PDF", "document", False, None),
    FileTypeSpec("docx", "Word", "document", False, None),
    FileTypeSpec("doc", "Word قدیمی", "document", False, None),
    FileTypeSpec("png", "تصویر", "image", False, None),
    FileTypeSpec("jpg", "تصویر", "image", False, None),
    FileTypeSpec("jpeg", "تصویر", "image", False, None),
)
