from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from app.agents.apple_notes import AppleNotesReadAgent, AppleNotesSearchAgent
from app.agents.file_search import FileSearchAgent
from app.agents.registry import AgentRegistry
from app.core.config import ConfigManager
from app.core.orchestrator import Orchestrator
from app.core.session import SessionStore
from app.llm.base import BaseLLMProvider
from app.llm.factory import create_provider
from app.models.schemas import (
    ProvidersStatusResponse,
    ProviderStatus,
    SessionResponse,
    SettingsSchema,
)

logger = logging.getLogger(__name__)


@dataclass
class AppState:
    config_manager: ConfigManager
    session_store: SessionStore
    registry: AgentRegistry
    provider: BaseLLMProvider
    orchestrator: Orchestrator
    auth_token: str | None


def get_app_state(app: FastAPI) -> AppState:
    return app.state.app_state  # type: ignore[attr-defined]


def _get_state(request: Request) -> AppState:
    return get_app_state(request.app)


@asynccontextmanager
async def lifespan(app: FastAPI):
    config_manager = ConfigManager()
    settings = config_manager.load()
    provider = create_provider(settings)
    session_store = SessionStore()
    registry = AgentRegistry()
    registry.register(FileSearchAgent())
    registry.register(AppleNotesSearchAgent())
    registry.register(AppleNotesReadAgent())
    orchestrator = Orchestrator(provider, registry, session_store)
    auth_token = os.environ.get("AUTH_TOKEN")

    app.state.app_state = AppState(
        config_manager=config_manager,
        session_store=session_store,
        registry=registry,
        provider=provider,
        orchestrator=orchestrator,
        auth_token=auth_token,
    )

    logger.info("Backend started (provider=%s)", settings.llm_provider)
    yield
    logger.info("Backend shutting down")


def create_app() -> FastAPI:
    application = FastAPI(
        title="AI Personal Assistant Backend",
        version="0.1.0",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"],
        allow_origin_regex=r"http://localhost:\d+",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/api/health", tags=["health"])
    async def health():
        return {"status": "ok"}

    @application.post("/api/sessions", response_model=SessionResponse, tags=["sessions"])
    async def create_session(request: Request):
        state = _get_state(request)
        session_id = state.session_store.create_session()
        return SessionResponse(session_id=session_id)

    @application.delete("/api/sessions/{session_id}", tags=["sessions"])
    async def delete_session(session_id: str, request: Request):
        state = _get_state(request)
        if not state.session_store.session_exists(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        state.session_store.delete_session(session_id)
        return {"status": "deleted"}

    @application.get("/api/settings", response_model=SettingsSchema, tags=["settings"])
    async def get_settings(request: Request):
        state = _get_state(request)
        settings = state.config_manager.load()
        redacted = settings.model_copy(deep=True)
        if redacted.azure_openai.api_key:
            redacted.azure_openai.api_key = "***"
        return redacted

    @application.put("/api/settings", response_model=SettingsSchema, tags=["settings"])
    async def update_settings(new_settings: SettingsSchema, request: Request):
        state = _get_state(request)
        state.config_manager.save(new_settings)
        state.provider = create_provider(new_settings)
        state.orchestrator = Orchestrator(
            state.provider, state.registry, state.session_store
        )
        redacted = new_settings.model_copy(deep=True)
        if redacted.azure_openai.api_key:
            redacted.azure_openai.api_key = "***"
        return redacted

    @application.get(
        "/api/settings/providers/status",
        response_model=ProvidersStatusResponse,
        tags=["settings"],
    )
    async def providers_status(request: Request):
        from app.llm.azure_openai_provider import AzureOpenAIProvider
        from app.llm.ollama_provider import OllamaProvider

        state = _get_state(request)
        settings = state.config_manager.load()
        ollama_provider = OllamaProvider(settings.ollama)
        azure_provider = AzureOpenAIProvider(settings.azure_openai)
        ollama_ok = await ollama_provider.health_check()
        azure_ok = await azure_provider.health_check()
        return ProvidersStatusResponse(
            ollama=ProviderStatus(available=ollama_ok),
            azure_openai=ProviderStatus(available=azure_ok),
        )

    from app.api.chat import router as chat_router
    application.include_router(chat_router)

    return application


app = create_app()
