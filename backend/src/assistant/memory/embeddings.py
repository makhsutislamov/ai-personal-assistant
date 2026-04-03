from __future__ import annotations

import functools

import ollama


@functools.lru_cache(maxsize=512)
def _cached_embedding(text: str) -> tuple[float, ...]:
    """Synchronous cached embedding call. Converted to tuple for hashability."""
    raise NotImplementedError("Use generate_embedding() async version")


async def generate_embedding(text: str) -> list[float]:
    """Generate an embedding for the given text via Ollama."""
    client = ollama.AsyncClient()
    response = await client.embeddings(model="nomic-embed-text", prompt=text)
    return response.embedding  # type: ignore[return-value]
