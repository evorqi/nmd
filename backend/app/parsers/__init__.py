from collections.abc import Callable

from app.domain.structure import ParseContext, WorkbookStructure
from app.parsers.csv_parser import parse_csv
from app.parsers.xls_parser import parse_xls
from app.parsers.xlsx_parser import parse_xlsx

Parser = Callable[[bytes, ParseContext], WorkbookStructure]

PARSERS: dict[str, Parser] = {
    "xlsx": parse_xlsx,
    "xls": parse_xls,
    "csv": parse_csv,
}


def get_parser(parser_key: str | None) -> Parser | None:
    if parser_key is None:
        return None
    return PARSERS.get(parser_key)
