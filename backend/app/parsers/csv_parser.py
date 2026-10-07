import csv
import io
from pathlib import Path

from app.domain.structure import ParseContext, WorkbookStructure
from app.errors import IngestionError
from app.messages import text
from app.parsers.common import build_sheet, workbook_from_sheets

_DELIMITERS = [",", ";", "\t", "|", "،"]


def parse_csv(content: bytes, context: ParseContext) -> WorkbookStructure:
    decoded = _decode_csv(content)
    if decoded.strip() == "":
        raise IngestionError("empty_workbook", text("empty_workbook"))
    delimiter = detect_delimiter(decoded)
    stem = Path(context.filename).stem.strip() or "CSV"
    try:
        rows = csv.reader(io.StringIO(decoded), delimiter=delimiter)
        sheet = build_sheet(stem[:31], rows, context.limits)
    except csv.Error as exc:
        raise IngestionError("unreadable_workbook", text("unreadable_workbook")) from exc
    return workbook_from_sheets("csv", [sheet])


def detect_delimiter(text_value: str) -> str:
    sample = text_value[:8192]
    best_delimiter = ","
    best_score = (-1, -1, -1)
    for index, delimiter in enumerate(_DELIMITERS):
        try:
            parsed = list(csv.reader(io.StringIO(sample), delimiter=delimiter))
        except csv.Error:
            continue
        rows = [row for row in parsed if any(cell.strip() for cell in row)]
        if not rows:
            continue
        widths = [len(row) for row in rows]
        widest = max(widths)
        consistent = 1 if widest > 1 and max(widths) == min(widths) else 0
        score = (widest, consistent, -index)
        if score > best_score:
            best_score = score
            best_delimiter = delimiter
    return best_delimiter


def _decode_csv(content: bytes) -> str:
    if content.startswith((b"\xff\xfe", b"\xfe\xff")):
        try:
            return content.decode("utf-16")
        except UnicodeDecodeError as exc:
            raise IngestionError("unreadable_workbook", text("unreadable_workbook")) from exc
    for encoding in ("utf-8-sig", "cp1256"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise IngestionError("unreadable_workbook", text("unreadable_workbook"))
