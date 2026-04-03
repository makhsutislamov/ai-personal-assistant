from __future__ import annotations

import time

from openai import AzureOpenAI


async def complete(
    prompt: str,
    endpoint: str,
    api_key: str,
    deployment: str,
    api_version: str = "2024-02-01",
) -> tuple[str, float]:
    """Call Azure OpenAI API and return (text, latency_ms)."""
    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=api_version,
    )
    start = time.perf_counter()
    response = client.chat.completions.create(
        model=deployment,
        messages=[{"role": "user", "content": prompt}],
    )
    latency_ms = (time.perf_counter() - start) * 1000
    text: str = response.choices[0].message.content or ""
    return text, latency_ms
