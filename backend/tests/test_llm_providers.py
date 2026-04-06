from __future__ import annotations

from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.llm.azure_openai_provider import AzureOpenAIProvider
from app.llm.factory import create_provider
from app.llm.ollama_provider import OllamaProvider
from app.models.schemas import (
    AzureOpenAISettings,
    ChatMessage,
    OllamaSettings,
    SettingsSchema,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def collect_stream(stream: AsyncIterator[str]) -> list[str]:
    tokens = []
    async for token in stream:
        tokens.append(token)
    return tokens


# ---------------------------------------------------------------------------
# OllamaProvider tests
# ---------------------------------------------------------------------------


class TestOllamaProvider:
    @pytest.fixture
    def settings(self):
        return OllamaSettings(base_url="http://localhost:11434", model="llama3.1")

    @pytest.mark.asyncio
    async def test_chat_completion_stream_yields_tokens(self, settings):
        async def _mock_stream():
            for content in ["Hello", " world", "!"]:
                msg = MagicMock()
                msg.message.content = content
                yield msg

        mock_client = AsyncMock()
        mock_client.chat.return_value = _mock_stream()

        provider = OllamaProvider(settings)
        provider._client = mock_client

        stream = await provider.chat_completion_stream(
            [ChatMessage(role="user", content="Hi")]
        )
        tokens = await collect_stream(stream)
        assert tokens == ["Hello", " world", "!"]

    @pytest.mark.asyncio
    async def test_health_check_returns_true(self, settings):
        mock_client = AsyncMock()
        mock_client.list.return_value = MagicMock()

        provider = OllamaProvider(settings)
        provider._client = mock_client

        assert await provider.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_returns_false_on_error(self, settings):
        mock_client = AsyncMock()
        mock_client.list.side_effect = ConnectionRefusedError("refused")

        provider = OllamaProvider(settings)
        provider._client = mock_client

        assert await provider.health_check() is False

    @pytest.mark.asyncio
    async def test_chat_completion_returns_chat_message(self, settings):
        mock_response = MagicMock()
        mock_response.message.role = "assistant"
        mock_response.message.content = "Test response"
        mock_response.message.tool_calls = None

        mock_client = AsyncMock()
        mock_client.chat.return_value = mock_response

        provider = OllamaProvider(settings)
        provider._client = mock_client

        result = await provider.chat_completion(
            [ChatMessage(role="user", content="Hello")]
        )
        assert result.role == "assistant"
        assert result.content == "Test response"


# ---------------------------------------------------------------------------
# AzureOpenAIProvider tests
# ---------------------------------------------------------------------------


class TestAzureOpenAIProvider:
    @pytest.fixture
    def settings(self):
        return AzureOpenAISettings(
            endpoint="https://test.openai.azure.com/",
            api_key="test-key",
            deployment="gpt-4o",
            api_version="2024-02-01",
        )

    @pytest.mark.asyncio
    async def test_chat_completion_stream_yields_tokens(self, settings):
        chunks = []
        for content in ["Hi", " there"]:
            chunk = MagicMock()
            chunk.choices = [MagicMock()]
            chunk.choices[0].delta.content = content
            chunks.append(chunk)

        async def _mock_stream_ctx():
            for ch in chunks:
                yield ch

        mock_stream = MagicMock()
        mock_stream.__aenter__ = AsyncMock(return_value=_mock_stream_ctx())
        mock_stream.__aexit__ = AsyncMock(return_value=False)

        mock_client = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_stream

        provider = AzureOpenAIProvider(settings)
        provider._client = mock_client

        stream = await provider.chat_completion_stream(
            [ChatMessage(role="user", content="Hi")]
        )
        tokens = await collect_stream(stream)
        assert tokens == ["Hi", " there"]

    @pytest.mark.asyncio
    async def test_health_check_returns_false_on_error(self, settings):
        mock_client = AsyncMock()
        mock_client.models.list.side_effect = Exception("auth error")

        provider = AzureOpenAIProvider(settings)
        provider._client = mock_client

        assert await provider.health_check() is False

    @pytest.mark.asyncio
    async def test_health_check_returns_true(self, settings):
        mock_client = AsyncMock()
        mock_client.models.list.return_value = MagicMock()

        provider = AzureOpenAIProvider(settings)
        provider._client = mock_client

        assert await provider.health_check() is True


# ---------------------------------------------------------------------------
# Factory tests
# ---------------------------------------------------------------------------


class TestCreateProvider:
    def test_creates_ollama_provider(self):
        settings = SettingsSchema(llm_provider="ollama")
        provider = create_provider(settings)
        assert isinstance(provider, OllamaProvider)

    def test_creates_azure_openai_provider(self):
        settings = SettingsSchema(llm_provider="azure_openai")
        provider = create_provider(settings)
        assert isinstance(provider, AzureOpenAIProvider)
