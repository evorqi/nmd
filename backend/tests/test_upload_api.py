import hashlib
from pathlib import Path

import pytest
from app.config import Settings
from app.factory import create_app
from app.orm import VersionRow
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from tests.conftest import make_settings, upload, xls_bytes, xlsx_bytes


def test_health(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_file_types_keep_future_formats_disabled(client: TestClient) -> None:
    response = client.get("/api/file-types")
    assert response.status_code == 200
    by_extension = {item["extension"]: item for item in response.json()["items"]}
    assert by_extension["xlsx"]["enabled"] is True
    assert by_extension["xls"]["enabled"] is True
    assert by_extension["csv"]["enabled"] is True
    assert by_extension["pdf"]["enabled"] is False
    assert by_extension["docx"]["enabled"] is False
    assert by_extension["png"]["enabled"] is False


def test_upload_xlsx_returns_structure_without_mutating_bytes(
    client: TestClient, settings: Settings
) -> None:
    content = xlsx_bytes(
        {
            "فروش": [["نام", "مبلغ"], ["علی رضایی", 5000000], ["رضا", 4200000]],
            "خالی": [],
        }
    )
    response = upload(client, "فروش شهریور.xlsx", content)
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["status"] == "stored"
    document = item["document"]
    assert document["original_filename"] == "فروش شهریور.xlsx"
    assert document["current_version_number"] == 0
    assert document["sha256"] == hashlib.sha256(content).hexdigest()
    version = document["version"]
    assert version["label"] == "original"
    assert version["version_number"] == 0
    structure = version["structure"]
    assert structure["sheet_count"] == 2
    assert structure["row_count"] == 3
    assert structure["sheets"][0]["name"] == "فروش"
    assert structure["sheets"][0]["headers"] == ["نام", "مبلغ"]
    assert structure["sheets"][0]["row_count"] == 3
    assert structure["sheets"][0]["data_row_count"] == 2
    assert structure["sheets"][0]["column_count"] == 2
    assert structure["sheets"][1]["row_count"] == 0
    stored = next(settings.data_dir.rglob("*.xlsx"))
    assert stored.read_bytes() == content
    assert stored.is_relative_to(settings.data_dir)
    assert ".." not in stored.parts
    assert "storage_relpath" not in response.text


def test_upload_xls_and_csv(client: TestClient) -> None:
    csv_content = "نام,مبلغ\nعلی,10\n".encode()
    response = client.post(
        "/api/uploads",
        files=[
            ("files", ("قدیم.xls", xls_bytes(), "application/octet-stream")),
            ("files", ("مشتری.csv", csv_content, "application/octet-stream")),
        ],
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["status"] for item in items] == ["stored", "stored"]
    assert items[0]["document"]["version"]["structure"]["file_type"] == "xls"
    assert items[0]["document"]["version"]["structure"]["sheets"][0]["headers"] == ["نام", "مبلغ"]
    assert items[1]["document"]["version"]["structure"]["sheets"][0]["name"] == "مشتری"
    assert items[1]["document"]["version"]["structure"]["sheets"][0]["data_row_count"] == 1


def test_reupload_creates_new_document_and_keeps_original_bytes(
    client: TestClient, settings: Settings
) -> None:
    content = "کد,مبلغ\n1,2\n".encode()
    first = upload(client, "a.csv", content)
    document_id = first.json()["items"][0]["document"]["id"]
    checksum = first.json()["items"][0]["document"]["sha256"]
    original_path = next(settings.data_dir.rglob("*.csv"))
    before = original_path.read_bytes()

    second = upload(client, "a.csv", content)
    assert second.json()["items"][0]["document"]["id"] != document_id
    assert original_path.read_bytes() == before == content
    fetched = client.get(f"/api/documents/{document_id}")
    assert fetched.status_code == 200
    assert fetched.json()["sha256"] == checksum
    assert fetched.json()["current_version_number"] == 0
    listed = client.get("/api/documents")
    assert len(listed.json()["items"]) == 2


def test_path_in_filename_does_not_escape_storage(client: TestClient, settings: Settings) -> None:
    content = "نام,مبلغ\nعلی,1\n".encode()
    response = upload(client, "../../فروش.csv", content)
    assert response.status_code == 200
    assert response.json()["items"][0]["document"]["original_filename"] == "فروش.csv"
    stored = next(settings.data_dir.rglob("*.csv"))
    assert stored.is_relative_to(settings.data_dir)
    assert stored.read_bytes() == content


def test_mixed_batch_keeps_valid_file_when_one_is_rejected(
    client: TestClient, settings: Settings
) -> None:
    response = client.post(
        "/api/uploads",
        files=[
            ("files", ("ok.csv", "نام,مبلغ\nعلی,1\n".encode(), "application/octet-stream")),
            ("files", ("scan.pdf", b"%PDF-1.4", "application/octet-stream")),
        ],
    )
    items = response.json()["items"]
    assert items[0]["status"] == "stored"
    assert items[1]["status"] == "rejected"
    assert items[1]["error"]["code"] == "file_type_not_enabled"
    assert len(list(settings.data_dir.rglob("*.csv"))) == 1
    assert list(settings.data_dir.rglob("*.pdf")) == []


def test_rejects_unsupported_corrupt_and_empty_files(
    client: TestClient, settings: Settings
) -> None:
    unsupported = upload(client, "macro.exe", b"MZ")
    assert unsupported.json()["items"][0]["error"]["code"] == "unsupported_file_type"
    corrupt = upload(client, "broken.xlsx", b"not-a-workbook")
    assert corrupt.json()["items"][0]["error"]["code"] == "unreadable_workbook"
    empty = upload(client, "empty.csv", b"")
    assert empty.json()["items"][0]["error"]["code"] == "empty_file"
    blank = upload(client, "blank.xlsx", xlsx_bytes({"خالی": []}))
    assert blank.json()["items"][0]["error"]["code"] == "empty_workbook"
    assert list(Path(settings.data_dir).glob("documents/*")) == []


def test_missing_upload_and_unknown_document(client: TestClient) -> None:
    missing = client.post("/api/uploads")
    assert missing.status_code == 400
    assert missing.json()["code"] == "no_files"
    unknown = client.get("/api/documents/missing")
    assert unknown.status_code == 404
    assert unknown.json()["code"] == "document_not_found"


def test_version_zero_cannot_be_replaced_over_http(client: TestClient) -> None:
    created = upload(client, "a.csv", "نام\nعلی\n".encode())
    document_id = created.json()["items"][0]["document"]["id"]
    replaced = client.put(f"/api/documents/{document_id}", json={"name": "other"})
    assert replaced.status_code == 405
    deleted = client.delete(f"/api/documents/{document_id}")
    assert deleted.status_code == 405


def test_request_limits_reject_before_storage(tmp_path: Path) -> None:
    too_many_settings = make_settings(tmp_path / "many", max_files_per_request=1)
    too_many_app = create_app(too_many_settings)
    with TestClient(too_many_app) as too_many_client:
        response = too_many_client.post(
            "/api/uploads",
            files=[
                ("files", ("a.csv", b"a\n1\n", "application/octet-stream")),
                ("files", ("b.csv", b"b\n1\n", "application/octet-stream")),
            ],
        )
    assert response.status_code == 400
    assert response.json()["code"] == "too_many_files"
    assert list((too_many_settings.data_dir).glob("documents/*")) == []

    large_settings = make_settings(tmp_path / "large", max_upload_bytes=16)
    large_app = create_app(large_settings)
    with TestClient(large_app) as large_client:
        response = upload(large_client, "big.csv", b"name,amount\n" + b"x" * 40)
    assert response.json()["items"][0]["error"]["code"] == "file_too_large"
    assert list(large_settings.data_dir.glob("documents/*")) == []

    row_settings = make_settings(tmp_path / "rows", max_rows_per_sheet=1)
    row_app = create_app(row_settings)
    with TestClient(row_app) as row_client:
        response = upload(row_client, "rows.csv", "نام\nعلی\n".encode())
    assert response.json()["items"][0]["error"]["code"] == "sheet_too_large"
    assert list(row_settings.data_dir.glob("documents/*")) == []


def test_version_row_requires_a_document(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    settings = make_settings(tmp_path / "fk")
    application = create_app(settings)
    session = application.state.session_factory()
    session.add(
        VersionRow(
            id="v",
            document_id="missing",
            version_number=0,
            label="original",
            storage_relpath="documents/missing/v0/a.csv",
            sha256="a" * 64,
            structure_json="{}",
            created_at=datetime.now(UTC),
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
    session.close()


def test_compressed_xlsx_over_limit_is_rejected(tmp_path: Path) -> None:
    settings = make_settings(tmp_path / "zip", max_uncompressed_bytes=50)
    application = create_app(settings)
    with TestClient(application) as zip_client:
        response = upload(zip_client, "a.xlsx", xlsx_bytes({"فروش": [["نام"], ["علی"]]}))
    assert response.json()["items"][0]["error"]["code"] == "uncompressed_too_large"
    assert list(settings.data_dir.rglob("*.xlsx")) == []
