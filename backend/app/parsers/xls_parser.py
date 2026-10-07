from collections.abc import Iterator

import xlrd
from xlrd.book import Book
from xlrd.sheet import Sheet

from app.domain.structure import ParseContext, WorkbookStructure
from app.errors import IngestionError
from app.messages import text
from app.parsers.common import build_sheet, workbook_from_sheets


def parse_xls(content: bytes, context: ParseContext) -> WorkbookStructure:
    try:
        book = xlrd.open_workbook(file_contents=content)
    except xlrd.XLRDError as exc:
        raise IngestionError("unreadable_workbook", text("unreadable_workbook")) from exc
    if book.nsheets > context.limits.max_sheets:
        raise IngestionError("too_many_sheets", text("too_many_sheets"))
    sheets = [
        build_sheet(
            book.sheet_by_index(index).name, _rows(book, book.sheet_by_index(index)), context.limits
        )
        for index in range(book.nsheets)
    ]
    return workbook_from_sheets("xls", sheets)


def _rows(book: Book, sheet: Sheet) -> Iterator[list[object]]:
    for row_index in range(sheet.nrows):
        yield [_cell_value(book, sheet.cell(row_index, column)) for column in range(sheet.ncols)]


def _cell_value(book: Book, cell: xlrd.sheet.Cell) -> object:
    if cell.ctype == xlrd.XL_CELL_DATE:
        try:
            return xlrd.xldate_as_datetime(cell.value, book.datemode)
        except (ValueError, xlrd.XLDateError):
            return cell.value
    if cell.ctype == xlrd.XL_CELL_ERROR:
        code = int(cell.value) if isinstance(cell.value, (int, float)) else -1
        return xlrd.error_text_from_code.get(code, "")
    if cell.ctype in {xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK}:
        return None
    return cell.value
