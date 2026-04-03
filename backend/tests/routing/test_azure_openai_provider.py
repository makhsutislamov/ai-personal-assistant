from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_azure_openai_complete():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Azure response"

    with patch("assistant.routing.providers.azure_openai_provider.AzureOpenAI") as mock_cls:
        mock_client = mock_cls.return_value
        mock_client.chat.completions.create.return_value = mock_response

        import asyncio

        from assistant.routing.providers.azure_openai_provider import complete

        text, latency = asyncio.get_event_loop().run_until_complete(
            complete(
                prompt="test prompt",
                endpoint="https://example.openai.azure.com",
                api_key="test-key",
                deployment="gpt-4o",
            )
        )

    assert text == "Azure response"
    assert latency >= 0
    mock_client.chat.completions.create.assert_called_once()
    call_kwargs = mock_client.chat.completions.create.call_args
    assert call_kwargs.kwargs["model"] == "gpt-4o"
    assert call_kwargs.kwargs["messages"][0]["content"] == "test prompt"


def test_azure_openai_empty_response():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = None

    with patch("assistant.routing.providers.azure_openai_provider.AzureOpenAI") as mock_cls:
        mock_client = mock_cls.return_value
        mock_client.chat.completions.create.return_value = mock_response

        import asyncio

        from assistant.routing.providers.azure_openai_provider import complete

        text, _ = asyncio.get_event_loop().run_until_complete(
            complete(
                prompt="test",
                endpoint="https://example.openai.azure.com",
                api_key="key",
                deployment="gpt-4o",
            )
        )

    assert text == ""
