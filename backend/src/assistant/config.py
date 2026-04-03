from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    memory_mode: Literal["auto", "ask", "manual"] = "ask"
    routing_preference: Literal["azure_openai", "ollama"] = "azure_openai"
    sensitive_local_only: bool = True

    ollama_base_url: str = "http://localhost:11434"

    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = ""
    azure_openai_api_version: str = "2024-02-01"

    db_path: str = "assistant.db"
    db_encryption_key: str = ""

    host: str = "127.0.0.1"
    port: int = 8765


def get_settings() -> Settings:
    return Settings()
