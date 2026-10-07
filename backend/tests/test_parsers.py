import pytest
from app.domain.structure import ParseContext, ParseLimits
from app.errors import IngestionError
from app.parsers.common import MAX_HEADER_LENGTH
from app.parsers.csv_parser import parse_csv
from app.parsers.xls_parser import parse_xls
from app.parsers.xlsx_parser import parse_xlsx
from tests.conftest import xls_bytes, xlsx_bytes


def _context(filename: str, max_rows_per_sheet: int = 100, max_columns: int = 20) -> ParseContext:
    return ParseContext(
        filename=filename,
        limits=ParseLimits(
            max_sheets=10, max_rows_per_sheet=max_rows_per_sheet, max_columns=max_columns
        ),
    )


def test_csv_preserves_arabic_letters_and_ignores_blank_rows() -> None:
    content = "علي,كالا\n\n1,2\n   \n".encode()
    sheet = parse_csv(content, _context("نام.csv")).sheets[0]
    assert sheet.headers == ("علي", "كالا")
    assert sheet.row_count == 2
    assert sheet.data_row_count == 1
    assert sheet.name == "نام"


def test_csv_detects_semicolon_arabic_comma_and_encodings() -> None:
    semicolon = parse_csv("نام;مبلغ\nعلی;10\n".encode(), _context("a.csv"))
    assert semicolon.sheets[0].column_count == 2
    arabic = parse_csv("نام،مبلغ\nعلی،۱۰\n".encode(), _context("b.csv"))
    assert arabic.sheets[0].headers == ("نام", "مبلغ")
    cp1256 = "نام,مبلغ\nرضا,10\n".encode("cp1256")
    assert parse_csv(cp1256, _context("c.csv")).sheets[0].headers[0] == "نام"
    titled = parse_csv("گزارش\nنام;مبلغ\nرضا;10\n".encode(), _context("title.csv"))
    assert titled.sheets[0].column_count == 2
    utf16 = "نام,مبلغ\nعلی,10\n".encode("utf-16")
    assert parse_csv(utf16, _context("d.csv")).sheets[0].data_row_count == 1


def test_csv_pads_short_header_when_a_later_row_is_wider() -> None:
    sheet = parse_csv("نام,مبلغ\nعلی,1,اضافه\n".encode(), _context("wide.csv")).sheets[0]
    assert sheet.column_count == 3
    assert sheet.headers == ("نام", "مبلغ", "")


def test_long_header_is_marked_truncated_for_the_summary_only() -> None:
    header = "ن" * (MAX_HEADER_LENGTH + 40)
    sheet = parse_csv(f"{header},مبلغ\n1,2\n".encode(), _context("long.csv")).sheets[0]
    assert sheet.headers_truncated is True
    assert sheet.headers[0] == "ن" * MAX_HEADER_LENGTH
    assert len(sheet.headers[0]) == MAX_HEADER_LENGTH


def test_empty_and_oversized_csv_are_rejected() -> None:
    with pytest.raises(IngestionError) as empty:
        parse_csv(b" \n", _context("empty.csv"))
    assert empty.value.code == "empty_workbook"
    with pytest.raises(IngestionError) as oversized:
        parse_csv("نام\nعلی\n".encode(), _context("rows.csv", max_rows_per_sheet=1))
    assert oversized.value.code == "sheet_too_large"


def test_xlsx_counts_formula_cells_and_keeps_empty_sheets() -> None:
    content = xlsx_bytes(
        {
            "گزارش": [["مبلغ"], ["=10+20"]],
            "خالی": [],
        }
    )
    structure = parse_xlsx(content, _context("گزارش.xlsx"))
    assert structure.file_type == "xlsx"
    assert structure.sheet_count == 2
    assert structure.sheets[0].row_count == 2
    assert structure.sheets[0].data_row_count == 1
    assert structure.sheets[0].headers == ("مبلغ",)
    assert structure.sheets[1].row_count == 0


def test_xlsx_without_data_or_with_corrupt_bytes_is_rejected() -> None:
    with pytest.raises(IngestionError) as empty:
        parse_xlsx(xlsx_bytes({"خالی": []}), _context("empty.xlsx"))
    assert empty.value.code == "empty_workbook"
    with pytest.raises(IngestionError) as corrupt:
        parse_xlsx(b"not-a-zip", _context("bad.xlsx"))
    assert corrupt.value.code == "unreadable_workbook"


def test_xls_reads_persian_headers() -> None:
    structure = parse_xls(xls_bytes(), _context("قدیم.xls"))
    sheet = structure.sheets[0]
    assert structure.file_type == "xls"
    assert sheet.name == "فروش"
    assert sheet.headers == ("نام", "مبلغ")
    assert sheet.data_row_count == 1
