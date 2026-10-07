from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import ingestion_error_response, router
from app.config import Settings, load_settings
from app.db import create_db_engine, create_schema, create_session_factory
from app.domain.registry import build_default_registry
from app.errors import IngestionError
from app.services.storage import FileStore


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or load_settings()
    resolved.data_dir.mkdir(parents=True, exist_ok=True)
    engine = create_db_engine(resolved)
    create_schema(engine)
    app = FastAPI(title="nmd", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.state.settings = resolved
    app.state.session_factory = create_session_factory(engine)
    app.state.store = FileStore(resolved.data_dir)
    app.state.registry = build_default_registry()
    app.include_router(router, prefix="/api")
    app.add_exception_handler(IngestionError, ingestion_error_response)
    return app
