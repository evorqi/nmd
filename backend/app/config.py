import os
from dataclasses import dataclass
from pathlib import Path

from app.domain.structure import ParseLimits


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    database_url: str
    max_upload_bytes: int = 20 * 1024 * 1024
    max_files_per_request: int = 10
    max_sheets: int = 100
    max_rows_per_sheet: int = 200_000
    max_columns: int = 512
    max_uncompressed_bytes: int = 200 * 1024 * 1024
    cors_origins: tuple[str, ...] = ("http://localhost:3000", "http://127.0.0.1:3000")

    def __post_init__(self) -> None:
        object.__setattr__(self, "data_dir", Path(self.data_dir).resolve())
        numeric = {
            "max_upload_bytes": self.max_upload_bytes,
            "max_files_per_request": self.max_files_per_request,
            "max_sheets": self.max_sheets,
            "max_rows_per_sheet": self.max_rows_per_sheet,
            "max_columns": self.max_columns,
            "max_uncompressed_bytes": self.max_uncompressed_bytes,
        }
        for name, value in numeric.items():
            if value <= 0:
                raise ValueError(f"{name} must be positive")
        if not self.cors_origins:
            raise ValueError("cors_origins must not be empty")

    @property
    def parse_limits(self) -> ParseLimits:
        return ParseLimits(
            max_sheets=self.max_sheets,
            max_rows_per_sheet=self.max_rows_per_sheet,
            max_columns=self.max_columns,
        )


def load_settings() -> Settings:
    backend_root = Path(__file__).resolve().parents[1]
    data_dir = Path(os.environ.get("NMD_DATA_DIR", backend_root / "data")).expanduser().resolve()
    database_url = os.environ.get(
        "NMD_DATABASE_URL",
        f"sqlite:///{(data_dir / 'nmd.sqlite3').as_posix()}",
    )
    origins = tuple(
        part.strip()
        for part in os.environ.get(
            "NMD_CORS_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000",
        ).split(",")
        if part.strip()
    )
    return Settings(
        data_dir=data_dir,
        database_url=database_url,
        max_upload_bytes=_env_int("NMD_MAX_UPLOAD_BYTES", 20 * 1024 * 1024),
        max_files_per_request=_env_int("NMD_MAX_FILES", 10),
        max_sheets=_env_int("NMD_MAX_SHEETS", 100),
        max_rows_per_sheet=_env_int("NMD_MAX_ROWS_PER_SHEET", 200_000),
        max_columns=_env_int("NMD_MAX_COLUMNS", 512),
        max_uncompressed_bytes=_env_int("NMD_MAX_UNCOMPRESSED_BYTES", 200 * 1024 * 1024),
        cors_origins=origins,
    )


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)
