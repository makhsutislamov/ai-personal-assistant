from __future__ import annotations

import logging
from copy import deepcopy

from fastapi import APIRouter, HTTPException

from app.models.schemas import ProviderStatus, ProvidersStatusResponse, SettingsSchema

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=SettingsSchema)
async def get_settings(request=None):
    from app.main import get_app_state
    from fastapi import Request

    # Accept either direct call or via dependency injection
    return _get_state(request).config_manager.load()


@router.put("", response_model=SettingsSchema)
async def update_settings(new_settings: SettingsSchema, request=None):
    from app.main import get_app_state
    from app.llm.factory import create_provider

    state = _get_state(request)
    state.config_manager.save(new_settings)

    # Recreate LLM provider with new settings
    state.provider = create_provider(new_settings)
    state.orchestrator = state.orchestrator.__class__(
        state.provider, state.registry, state.session_store
    )

    return new_settings


@router.get("/providers/status", response_model=ProvidersStatusResponse)
async def providers_status(request=None):
    from app.llm.ollama_provider import OllamaProvider
    from app.llm.azure_openai_provider import AzureOpenAIProvider

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


def _get_state(request):
    from app.main import get_app_state

    if request is None:
        raise HTTPException(status_code=500, detail="No request context")
    return get_app_state(request.app)
