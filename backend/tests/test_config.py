from __future__ import annotations

import pytest
from pydantic import ValidationError

from assistant.config import Settings


def test_defaults():
    s = Settings()
    assert s.memory_mode == "ask"
    assert s.routing_preference == "azure_openai"
    assert s.sensitive_local_only is True
    assert s.ollama_base_url == "http://localhost:11434"
    assert s.azure_openai_api_version == "2024-02-01"


def test_env_override(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MEMORY_MODE", "auto")
    monkeypatch.setenv("ROUTING_PREFERENCE", "ollama")
    monkeypatch.setenv("SENSITIVE_LOCAL_ONLY", "false")
    s = Settings()
    assert s.memory_mode == "auto"
    assert s.routing_preference == "ollama"
    assert s.sensitive_local_only is False


def test_invalid_memory_mode():
    with pytest.raises(ValidationError):
        Settings(memory_mode="invalid")  # type: ignore[call-arg]


def test_invalid_routing_preference():
    with pytest.raises(ValidationError):
        Settings(routing_preference="gpt4o")  # type: ignore[call-arg]
