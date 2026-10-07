import pytest
from app.domain.filenames import display_filename, extension_of, sanitize_storage_name
from app.domain.registry import FileTypeSpec, build_default_registry
from app.errors import IngestionError


def test_spreadsheet_types_resolve_and_future_types_stay_disabled() -> None:
    registry = build_default_registry()
    assert registry.resolve("Report.XLSX").parser_key == "xlsx"
    assert registry.resolve("old.xls").extension == "xls"
    assert registry.resolve("data.csv").enabled is True
    pdf = registry.get("pdf")
    assert pdf is not None
    assert pdf.enabled is False
    with pytest.raises(IngestionError) as disabled:
        registry.resolve("scan.PDF")
    assert disabled.value.code == "file_type_not_enabled"
    with pytest.raises(IngestionError) as unknown:
        registry.resolve("macro.exe")
    assert unknown.value.code == "unsupported_file_type"


def test_new_type_registration_does_not_change_other_registries() -> None:
    first = build_default_registry()
    first.register(FileTypeSpec("tsv", "TSV", "spreadsheet", True, "csv"))
    assert first.resolve("table.tsv").parser_key == "csv"
    second = build_default_registry()
    with pytest.raises(IngestionError) as caught:
        second.resolve("table.tsv")
    assert caught.value.code == "unsupported_file_type"


def test_filename_helpers_drop_paths_and_keep_persian_names() -> None:
    assert display_filename("../../فروش شهریور.xlsx") == "فروش شهریور.xlsx"
    assert extension_of(r"..\secret.XLS") == "xls"
    stored = sanitize_storage_name("../../فروش شهریور.xlsx")
    assert stored == "فروش شهریور.xlsx"
    assert "/" not in stored
    assert "\\" not in stored
    with pytest.raises(IngestionError) as caught:
        display_filename("..")
    assert caught.value.code == "invalid_filename"
