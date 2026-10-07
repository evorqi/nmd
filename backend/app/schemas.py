from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.domain.structure import SheetStructure, WorkbookStructure


class SheetOut(BaseModel):
    name: str
    row_count: int
    data_row_count: int
    column_count: int
    headers: list[str]
    headers_truncated: bool


class StructureOut(BaseModel):
    file_type: str
    sheet_count: int
    row_count: int
    sheets: list[SheetOut]


class VersionOut(BaseModel):
    id: str
    version_number: int
    label: str
    sha256: str
    created_at: datetime
    structure: StructureOut


class DocumentOut(BaseModel):
    id: str
    original_filename: str
    extension: str
    byte_size: int
    sha256: str
    current_version_number: int
    created_at: datetime
    version: VersionOut | None = None


class ItemError(BaseModel):
    code: str
    message: str


class UploadItemOut(BaseModel):
    filename: str
    status: Literal["stored", "rejected"]
    document: DocumentOut | None = None
    error: ItemError | None = None


class UploadBatchOut(BaseModel):
    items: list[UploadItemOut]


class FileTypeOut(BaseModel):
    extension: str
    label: str
    kind: str
    enabled: bool


class FileTypeListOut(BaseModel):
    items: list[FileTypeOut]


class DocumentListOut(BaseModel):
    items: list[DocumentOut]


class ErrorOut(BaseModel):
    code: str
    message: str


class HealthOut(BaseModel):
    status: str = Field(default="ok")


def structure_out(structure: WorkbookStructure) -> StructureOut:
    return StructureOut(
        file_type=structure.file_type,
        sheet_count=structure.sheet_count,
        row_count=structure.row_count,
        sheets=[_sheet_out(sheet) for sheet in structure.sheets],
    )


def _sheet_out(sheet: SheetStructure) -> SheetOut:
    return SheetOut(
        name=sheet.name,
        row_count=sheet.row_count,
        data_row_count=sheet.data_row_count,
        column_count=sheet.column_count,
        headers=list(sheet.headers),
        headers_truncated=sheet.headers_truncated,
    )
