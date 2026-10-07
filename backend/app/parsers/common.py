import math
from collections.abc import Iterable, Sequence
from datetime import date, datetime

from app.domain.structure import ParseLimits, SheetStructure, WorkbookStructure
from app.errors import IngestionError
from app.messages import sheet_too_large, text, too_many_columns

MAX_HEADER_LENGTH = 500


def cell_to_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="seconds")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return ""
        if value.is_integer():
            return str(int(value))
        return str(value)
    if isinstance(value, int):
        return str(value)
    return str(value).replace("\xa0", " ").strip()


def build_sheet(name: str, rows: Iterable[Sequence[object]], limits: ParseLimits) -> SheetStructure:
    header: list[str] | None = None
    row_count = 0
    column_count = 0
    for raw_row in rows:
        texts = [cell_to_text(cell) for cell in raw_row]
        while texts and texts[-1] == "":
            texts.pop()
        if not any(texts):
            continue
        if len(texts) > limits.max_columns:
            raise IngestionError("too_many_columns", too_many_columns(name))
        row_count += 1
        if row_count > limits.max_rows_per_sheet:
            raise IngestionError("sheet_too_large", sheet_too_large(name))
        column_count = max(column_count, len(texts))
        if header is None:
            header = texts
    if header is None:
        return SheetStructure(
            name=name,
            row_count=0,
            data_row_count=0,
            column_count=0,
            headers=(),
            headers_truncated=False,
        )
    if len(header) < column_count:
        header = [*header, *[""] * (column_count - len(header))]
    clipped: list[str] = []
    truncated = False
    for cell in header:
        if len(cell) > MAX_HEADER_LENGTH:
            clipped.append(cell[:MAX_HEADER_LENGTH])
            truncated = True
        else:
            clipped.append(cell)
    return SheetStructure(
        name=name,
        row_count=row_count,
        data_row_count=row_count - 1,
        column_count=column_count,
        headers=tuple(clipped),
        headers_truncated=truncated,
    )


def workbook_from_sheets(file_type: str, sheets: list[SheetStructure]) -> WorkbookStructure:
    if not sheets or all(sheet.row_count == 0 for sheet in sheets):
        raise IngestionError("empty_workbook", text("empty_workbook"))
    return WorkbookStructure(
        file_type=file_type,
        sheet_count=len(sheets),
        row_count=sum(sheet.row_count for sheet in sheets),
        sheets=tuple(sheets),
    )
