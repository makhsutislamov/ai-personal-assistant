from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from assistant.telemetry.setup import setup_telemetry


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    from assistant.config import Settings
    from assistant.db.engine import create_engine, create_session_factory
    from assistant.db.migrations import run_migrations
    from assistant.deps import set_session_factory

    settings = Settings()
    engine = create_engine(settings.db_path, settings.db_encryption_key)
    await run_migrations(engine)
    set_session_factory(create_session_factory(engine))

    yield

    await engine.dispose()


def create_app() -> FastAPI:
    setup_telemetry()

    app = FastAPI(
        title="AI Personal Assistant",
        version="0.1.0",
        description="Local AI assistant backend",
        lifespan=_lifespan,
    )


    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from assistant.telemetry.middleware import TelemetryMiddleware
    app.add_middleware(TelemetryMiddleware)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    from assistant.api import (
        audit,
        chat,
        evaluation,
        integrations,
        memory,
        retrieval,
        settings,
        tasks,
    )

    app.include_router(chat.router, prefix="/v1")
    app.include_router(memory.router, prefix="/v1")
    app.include_router(retrieval.router, prefix="/v1")
    app.include_router(settings.router, prefix="/v1")
    app.include_router(tasks.router, prefix="/v1")
    app.include_router(audit.router, prefix="/v1")
    app.include_router(integrations.router, prefix="/v1")
    app.include_router(evaluation.router, prefix="/v1")

    return app
