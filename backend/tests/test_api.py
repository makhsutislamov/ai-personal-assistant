from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from typing import AsyncIterator

from app.agents.registry import AgentRegistry
from app.core.config import ConfigManager
from app.core.orchestrator import Orchestrator
from app.core.session import SessionStore
from app.llm.base import BaseLLMProvider
from app.main import AppState, create_app
from app.models.schemas import ChatMessage, SettingsSchema


class MockProvider(BaseLLMProvider):
    async def chat_completion(self, messages, tools=None) -> ChatMessage:
        return ChatMessage(role="assistant", content="mock response")

    async def chat_completion_stream(self, messages, tools=None) -> AsyncIterator[str]:
        async def _gen():
            yield "mock"
        return _gen()

    async def health_check(self) -> bool:
        return True


@pytest.fixture
def app_and_state(tmp_path):
    """Create app and inject mock state, bypassing lifespan."""
    application = create_app()

    config_manager = ConfigManager(config_dir=tmp_path)
    session_store = SessionStore()
    registry = AgentRegistry()
    provider = MockProvider()
    orchestrator = Orchestrator(provider, registry, session_store)

    state = AppState(
        config_manager=config_manager,
        session_store=session_store,
        registry=registry,
        provider=provider,
        orchestrator=orchestrator,
        auth_token=None,
    )
    application.state.app_state = state
    return application, state


@pytest.fixture
def client(app_and_state):
    application, _ = app_and_state
    # Use lifespan=False to skip the default lifespan and use injected state
    with TestClient(application, raise_server_exceptions=True) as c:
        # Re-inject state after the lifespan overwrites it
        application.state.app_state = app_and_state[1]
        yield c


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestSessionsEndpoints:
    def test_create_session_returns_session_id(self, client):
        response = client.post("/api/sessions")
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert len(data["session_id"]) > 0

    def test_delete_session_returns_200(self, client):
        create_resp = client.post("/api/sessions")
        session_id = create_resp.json()["session_id"]
        delete_resp = client.delete(f"/api/sessions/{session_id}")
        assert delete_resp.status_code == 200

    def test_delete_nonexistent_session_returns_404(self, client):
        response = client.delete("/api/sessions/doesnotexist")
        assert response.status_code == 404


class TestSettingsEndpoints:
    def test_get_settings_returns_defaults(self, client):
        response = client.get("/api/settings")
        assert response.status_code == 200
        data = response.json()
        assert data["llm_provider"] == "ollama"

    def test_put_settings_valid(self, client):
        payload = {
            "llm_provider": "ollama",
            "ollama": {"base_url": "http://custom:11434", "model": "llama3.2"},
            "azure_openai": {
                "endpoint": "",
                "api_key": "",
                "deployment": "",
                "api_version": "2024-02-01",
            },
        }
        response = client.put("/api/settings", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["ollama"]["model"] == "llama3.2"

    def test_put_settings_invalid_returns_422(self, client):
        payload = {"llm_provider": "unknown_provider"}
        response = client.put("/api/settings", json=payload)
        assert response.status_code == 422

    def test_api_key_redacted_in_response(self, client):
        payload = {
            "llm_provider": "azure_openai",
            "ollama": {"base_url": "http://localhost:11434", "model": "llama3.1"},
            "azure_openai": {
                "endpoint": "https://test.openai.azure.com/",
                "api_key": "super-secret-key",
                "deployment": "gpt-4o",
                "api_version": "2024-02-01",
            },
        }
        response = client.put("/api/settings", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["azure_openai"]["api_key"] == "***"
