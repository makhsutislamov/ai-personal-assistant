from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from assistant.config import Settings
from assistant.policy.guard import PolicyDecision
from assistant.routing import router


def _clean_decision() -> PolicyDecision:
    return PolicyDecision(allowed_remote=True, sensitivity_class="clean", reason="ok")


def _sensitive_decision() -> PolicyDecision:
    return PolicyDecision(
        allowed_remote=False,
        sensitivity_class="sensitive",
        reason="blocked",
        blocked_patterns=["api_key"],
    )


@pytest.fixture(autouse=True)
def reset_circuit_breaker():
    """Reset circuit breaker state between tests."""
    router._azure_cb._failures.clear()
    yield
    router._azure_cb._failures.clear()


async def test_sensitive_routes_to_ollama():
    """Sensitive content must always go to Ollama regardless of routing preference."""
    settings = Settings(routing_preference="azure_openai")

    with patch(
        "assistant.routing.providers.ollama.complete",
        new=AsyncMock(return_value=("local response", 10.0)),
    ) as mock_ollama, patch(
        "assistant.routing.providers.azure_openai_provider.complete",
        new=AsyncMock(return_value=("remote response", 20.0)),
    ) as mock_azure:
        result = await router.invoke("secret prompt", _sensitive_decision(), settings)

    assert result.provider == "ollama"
    assert result.text == "local response"
    mock_azure.assert_not_called()


async def test_non_sensitive_azure_preferred():
    """Non-sensitive content with azure_openai preference should use Azure."""
    settings = Settings(
        routing_preference="azure_openai",
        azure_openai_endpoint="https://x.openai.azure.com",
        azure_openai_api_key="key",
        azure_openai_deployment="gpt-4o",
    )

    with patch(
        "assistant.routing.providers.azure_openai_provider.complete",
        new=AsyncMock(return_value=("azure response", 15.0)),
    ) as mock_azure:
        result = await router.invoke("normal prompt", _clean_decision(), settings)

    assert result.provider == "azure_openai"
    assert result.text == "azure response"
    mock_azure.assert_called_once()


async def test_non_sensitive_ollama_preferred():
    """Non-sensitive content with ollama preference should use Ollama."""
    settings = Settings(routing_preference="ollama")

    with patch(
        "assistant.routing.providers.ollama.complete",
        new=AsyncMock(return_value=("ollama response", 5.0)),
    ) as mock_ollama:
        result = await router.invoke("normal prompt", _clean_decision(), settings)

    assert result.provider == "ollama"
    mock_ollama.assert_called_once()


async def test_circuit_breaker_fallback_to_ollama():
    """After 3 failures, subsequent calls should fall back to Ollama."""
    settings = Settings(
        routing_preference="azure_openai",
        azure_openai_endpoint="https://x.openai.azure.com",
        azure_openai_api_key="key",
        azure_openai_deployment="gpt-4o",
    )

    # Trigger 3 failures to open circuit breaker
    with patch(
        "assistant.routing.providers.azure_openai_provider.complete",
        new=AsyncMock(side_effect=Exception("connection error")),
    ), patch(
        "assistant.routing.providers.ollama.complete",
        new=AsyncMock(return_value=("fallback", 5.0)),
    ):
        for _ in range(3):
            try:
                await router.invoke("prompt", _clean_decision(), settings)
            except Exception:
                pass

    # Circuit is now open — next call should go directly to Ollama
    assert router._azure_cb.is_open()

    with patch(
        "assistant.routing.providers.ollama.complete",
        new=AsyncMock(return_value=("fallback response", 5.0)),
    ) as mock_ollama, patch(
        "assistant.routing.providers.azure_openai_provider.complete",
        new=AsyncMock(return_value=("azure", 10.0)),
    ) as mock_azure:
        result = await router.invoke("prompt", _clean_decision(), settings)

    assert result.provider == "ollama"
    mock_azure.assert_not_called()
