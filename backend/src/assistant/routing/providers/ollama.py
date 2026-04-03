from __future__ import annotations

import time

import ollama


async def complete(prompt: str, model: str) -> tuple[str, float]:
    """Call Ollama chat API and return (text, latency_ms)."""
    start = time.perf_counter()
    response = await ollama.AsyncClient().chat(  # type: ignore[attr-defined]
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    latency_ms = (time.perf_counter() - start) * 1000
    text: str = response.message.content or ""
    return text, latency_ms
