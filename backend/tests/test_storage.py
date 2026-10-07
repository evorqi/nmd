from pathlib import Path

import pytest
from app.domain.registry import build_default_registry
from app.errors import IngestionError
from app.services.ingestion import IncomingFile, IngestionService
from app.services.storage import FileStore
from tests.conftest import make_settings


def test_original_write_is_exclusive_and_cannot_escape_root(tmp_path: Path) -> None:
    store = FileStore(tmp_path)
    content = "نام,مبلغ\n".encode()
    stored = store.write_new("doc-1", "فروش.csv", content)
    assert store.read(stored.relative_path) == content
    with pytest.raises(IngestionError) as conflict:
        store.write_new("doc-1", "فروش.csv", b"changed\n")
    assert conflict.value.code == "storage_conflict"
    assert store.read(stored.relative_path) == content
    for escape in ("../secret.csv", "/etc/passwd", "documents/../../secret.csv"):
        with pytest.raises(IngestionError) as invalid:
            store.read(escape)
        assert invalid.value.code == "invalid_storage_path"


def test_discard_removes_failed_original(tmp_path: Path) -> None:
    store = FileStore(tmp_path)
    stored = store.write_new("doc-2", "a.csv", b"a,b\n")
    store.discard(stored.relative_path)
    assert list(tmp_path.rglob("*.csv")) == []
    assert list((tmp_path / "documents").glob("*")) == []


def test_database_failure_does_not_keep_a_partial_original(tmp_path: Path) -> None:
    settings = make_settings(tmp_path / "db-fail")

    class FailingSession:
        def add(self, _obj: object) -> None:
            return None

        def commit(self) -> None:
            raise RuntimeError("database unavailable")

        def rollback(self) -> None:
            return None

        def close(self) -> None:
            return None

    store = FileStore(settings.data_dir)
    service = IngestionService(
        settings=settings,
        session_factory=lambda: FailingSession(),  # type: ignore[arg-type,return-value]
        store=store,
        registry=build_default_registry(),
    )
    result = service.ingest([IncomingFile(filename="a.csv", content="نام,مبلغ\nعلی,1\n".encode())])
    assert result.items[0].status == "rejected"
    assert result.items[0].error is not None
    assert result.items[0].error.code == "internal_error"
    assert list(settings.data_dir.rglob("*.csv")) == []
