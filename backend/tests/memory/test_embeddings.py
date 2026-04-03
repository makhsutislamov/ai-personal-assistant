from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from assistant.memory.embeddings import generate_embedding


async def test_generate_embedding_shape():
    mock_response = MagicMock()
    mock_response.embedding = [0.1, 0.2, 0.3, 0.4]

    with patch("ollama.AsyncClient") as mock_client_cls:
        mock_instance = mock_client_cls.return_value
        mock_instance.embeddings = AsyncMock(return_value=mock_response)

        result = await generate_embedding("hello world")

    assert result == [0.1, 0.2, 0.3, 0.4]
    mock_instance.embeddings.assert_called_once_with(
        model="nomic-embed-text", prompt="hello world"
    )
