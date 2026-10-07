"""Workbook ingestion.

Upload stores an immutable original version and a structural summary.
It does not clean, match, or interpret column meaning.
"""

import hashlib
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.domain.filenames import display_filename
from app.domain.registry import FileTypeRegistry
from app.domain.structure import ParseContext
from app.errors import IngestionError
from app.messages import text
from app.orm import DocumentRow, VersionRow
from app.parsers import get_parser
from app.parsers.xlsx_parser import assert_zip_container_safe
from app.schemas import (
    DocumentListOut,
    DocumentOut,
    ItemError,
    StructureOut,
    UploadBatchOut,
    UploadItemOut,
    VersionOut,
    structure_out,
)
from app.services.storage import FileStore

logger = logging.getLogger("nmd.ingestion")

ORIGINAL_LABEL = "original"


@dataclass(frozen=True)
class IncomingFile:
    filename: str
    content: bytes
    too_large: bool = False


class IngestionService:
    def __init__(
        self,
        settings: Settings,
        session_factory: Callable[[], Session],
        store: FileStore,
        registry: FileTypeRegistry,
    ) -> None:
        self.settings = settings
        self.session_factory = session_factory
        self.store = store
        self.registry = registry

    def ingest(self, incoming: list[IncomingFile]) -> UploadBatchOut:
        if not incoming:
            raise IngestionError("no_files", text("no_files"), 400)
        if len(incoming) > self.settings.max_files_per_request:
            raise IngestionError("too_many_files", text("too_many_files"), 400)
        return UploadBatchOut(items=[self._ingest_one(item) for item in incoming])

    def list_documents(self) -> DocumentListOut:
        session = self.session_factory()
        try:
            documents = session.scalars(
                select(DocumentRow).order_by(DocumentRow.created_at.desc())
            ).all()
            versions = self._versions_for(session, [document.id for document in documents])
            items = [
                _document_out(
                    document,
                    versions.get((document.id, document.current_version_number)),
                )
                for document in documents
            ]
            return DocumentListOut(items=items)
        finally:
            session.close()

    def get_document(self, document_id: str) -> DocumentOut:
        session = self.session_factory()
        try:
            document = session.get(DocumentRow, document_id)
            if document is None:
                raise IngestionError("document_not_found", text("document_not_found"), 404)
            version = session.scalar(
                select(VersionRow).where(
                    VersionRow.document_id == document.id,
                    VersionRow.version_number == document.current_version_number,
                )
            )
            return _document_out(document, version)
        finally:
            session.close()

    def _ingest_one(self, item: IncomingFile) -> UploadItemOut:
        shown_name = item.filename.strip() or item.filename
        try:
            filename = display_filename(item.filename)
            shown_name = filename
            if item.too_large or len(item.content) > self.settings.max_upload_bytes:
                raise IngestionError("file_too_large", text("file_too_large"))
            if len(item.content) == 0:
                raise IngestionError("empty_file", text("empty_file"))
            spec = self.registry.resolve(filename)
            if spec.extension == "xlsx":
                assert_zip_container_safe(item.content, self.settings.max_uncompressed_bytes)
            parser = get_parser(spec.parser_key)
            if parser is None:
                raise IngestionError("parser_not_available", text("parser_not_available"))
            structure = parser(
                item.content, ParseContext(filename=filename, limits=self.settings.parse_limits)
            )
            document = self._persist(
                filename, spec.extension, item.content, structure_out(structure)
            )
            return UploadItemOut(filename=filename, status="stored", document=document, error=None)
        except IngestionError as exc:
            return UploadItemOut(
                filename=shown_name,
                status="rejected",
                document=None,
                error=ItemError(code=exc.code, message=exc.message),
            )
        except Exception:
            logger.exception("ingestion failed for %s", shown_name)
            return UploadItemOut(
                filename=shown_name,
                status="rejected",
                document=None,
                error=ItemError(code="internal_error", message=text("internal_error")),
            )

    def _persist(
        self, filename: str, extension: str, content: bytes, structure: StructureOut
    ) -> DocumentOut:
        document_id = str(uuid.uuid4())
        version_id = str(uuid.uuid4())
        stored = self.store.write_new(document_id, filename, content)
        read_back = self.store.read(stored.relative_path)
        if read_back != content or hashlib.sha256(read_back).hexdigest() != stored.sha256:
            self.store.discard(stored.relative_path)
            raise IngestionError("storage_integrity", text("storage_integrity"))
        created_at = datetime.now(UTC).replace(microsecond=0)
        session = self.session_factory()
        try:
            session.add(
                DocumentRow(
                    id=document_id,
                    original_filename=filename,
                    extension=extension,
                    byte_size=stored.byte_size,
                    sha256=stored.sha256,
                    current_version_number=0,
                    created_at=created_at,
                )
            )
            session.add(
                VersionRow(
                    id=version_id,
                    document_id=document_id,
                    version_number=0,
                    label=ORIGINAL_LABEL,
                    storage_relpath=stored.relative_path,
                    sha256=stored.sha256,
                    structure_json=structure.model_dump_json(),
                    created_at=created_at,
                )
            )
            session.commit()
        except Exception:
            session.rollback()
            self.store.discard(stored.relative_path)
            raise
        finally:
            session.close()
        return DocumentOut(
            id=document_id,
            original_filename=filename,
            extension=extension,
            byte_size=stored.byte_size,
            sha256=stored.sha256,
            current_version_number=0,
            created_at=created_at,
            version=VersionOut(
                id=version_id,
                version_number=0,
                label=ORIGINAL_LABEL,
                sha256=stored.sha256,
                created_at=created_at,
                structure=structure,
            ),
        )

    def _versions_for(
        self, session: Session, document_ids: list[str]
    ) -> dict[tuple[str, int], VersionRow]:
        if not document_ids:
            return {}
        rows = session.scalars(
            select(VersionRow).where(VersionRow.document_id.in_(document_ids))
        ).all()
        return {(row.document_id, row.version_number): row for row in rows}


def _document_out(document: DocumentRow, version: VersionRow | None) -> DocumentOut:
    version_out = None
    if version is not None:
        version_out = VersionOut(
            id=version.id,
            version_number=version.version_number,
            label=version.label,
            sha256=version.sha256,
            created_at=_as_utc(version.created_at),
            structure=StructureOut.model_validate_json(version.structure_json),
        )
    return DocumentOut(
        id=document.id,
        original_filename=document.original_filename,
        extension=document.extension,
        byte_size=document.byte_size,
        sha256=document.sha256,
        current_version_number=document.current_version_number,
        created_at=_as_utc(document.created_at),
        version=version_out,
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
