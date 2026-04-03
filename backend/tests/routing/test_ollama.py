from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch


async def test_ollama_complete_returns_text():
    mock_response = MagicMock()
    mock_response.message.content = "Hello from Ollama"

    with patch("ollama.AsyncClient") as mock_client_class:
        mock_instance = mock_client_class.return_value
        mock_instance.chat = AsyncMock(return_value=mock_response)

        from assistant.routing.providers import ollama as ollama_provider
        text, latency = await ollama_provider.complete("test prompt", model="llama3.2")

    assert text == "Hello from Ollama"
    assert latency >= 0
    mock_instance.chat.assert_called_once_with(
        model="llama3.2",
        messages=[{"role": "user", "content": "test prompt"}],
    )


async def test_ollama_empty_response():
    mock_response = MagicMock()
    mock_response.message.content = None

    with patch("ollama.AsyncClient") as mock_client_class:
        mock_instance = mock_client_class.return_value
        mock_instance.chat = AsyncMock(return_value=mock_response)

        from assistant.routing.providers import ollama as ollama_provider
        text, _ = await ollama_provider.complete("test", model="llama3.2")

    assert text == ""
