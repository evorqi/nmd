import asyncio

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import JSONResponse

from app.errors import IngestionError
from app.messages import text
from app.schemas import (
    DocumentListOut,
    DocumentOut,
    ErrorOut,
    FileTypeListOut,
    FileTypeOut,
    HealthOut,
    UploadBatchOut,
)
from app.services.ingestion import IncomingFile, IngestionService

router = APIRouter()
_OPTIONAL_FILES = File(default=None)


def ingestion_error_response(_request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, IngestionError):
        return JSONResponse(
            status_code=500,
            content={"code": "internal_error", "message": "خطای داخلی رخ داد."},
        )
    payload = ErrorOut(code=exc.code, message=exc.message)
    return JSONResponse(status_code=exc.status_code, content=payload.model_dump())


def service_from(request: Request) -> IngestionService:
    return IngestionService(
        settings=request.app.state.settings,
        session_factory=request.app.state.session_factory,
        store=request.app.state.store,
        registry=request.app.state.registry,
    )


@router.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    return HealthOut()


@router.get("/file-types", response_model=FileTypeListOut)
def file_types(request: Request) -> FileTypeListOut:
    specs = request.app.state.registry.list_types()
    return FileTypeListOut(
        items=[
            FileTypeOut(
                extension=spec.extension, label=spec.label, kind=spec.kind, enabled=spec.enabled
            )
            for spec in specs
        ]
    )


@router.get("/documents", response_model=DocumentListOut)
def list_documents(request: Request) -> DocumentListOut:
    return service_from(request).list_documents()


@router.get("/documents/{document_id}", response_model=DocumentOut)
def get_document(document_id: str, request: Request) -> DocumentOut:
    return service_from(request).get_document(document_id)


@router.post("/uploads", response_model=UploadBatchOut)
async def upload_files(
    request: Request,
    files: list[UploadFile] | None = _OPTIONAL_FILES,
) -> UploadBatchOut:
    if not files:
        raise IngestionError("no_files", text("no_files"), 400)
    settings = request.app.state.settings
    incoming: list[IncomingFile] = []
    for upload in files:
        content, too_large = await _read_capped(upload, settings.max_upload_bytes)
        incoming.append(
            IncomingFile(filename=upload.filename or "", content=content, too_large=too_large)
        )
    service = service_from(request)
    return await asyncio.to_thread(service.ingest, incoming)


async def _read_capped(upload: UploadFile, max_bytes: int) -> tuple[bytes, bool]:
    chunks: list[bytes] = []
    size = 0
    try:
        while True:
            chunk = await upload.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > max_bytes:
                return b"", True
            chunks.append(chunk)
        return b"".join(chunks), False
    finally:
        await upload.close()
