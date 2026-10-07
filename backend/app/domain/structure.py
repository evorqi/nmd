from dataclasses import dataclass


@dataclass(frozen=True)
class ParseLimits:
    max_sheets: int
    max_rows_per_sheet: int
    max_columns: int


@dataclass(frozen=True)
class ParseContext:
    filename: str
    limits: ParseLimits


@dataclass(frozen=True)
class SheetStructure:
    name: str
    row_count: int
    data_row_count: int
    column_count: int
    headers: tuple[str, ...]
    headers_truncated: bool


@dataclass(frozen=True)
class WorkbookStructure:
    file_type: str
    sheet_count: int
    row_count: int
    sheets: tuple[SheetStructure, ...]
