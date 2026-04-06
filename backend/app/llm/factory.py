from __future__ import annotations

from app.llm.azure_openai_provider import AzureOpenAIProvider
from app.llm.base import BaseLLMProvider
from app.llm.ollama_provider import OllamaProvider
from app.models.schemas import SettingsSchema


def create_provider(settings: SettingsSchema) -> BaseLLMProvider:
    if settings.llm_provider == "ollama":
        return OllamaProvider(settings.ollama)
    elif settings.llm_provider == "azure_openai":
        return AzureOpenAIProvider(settings.azure_openai)
    else:
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider!r}")
