from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ModelResponse:
    text: str
    model_used: str
    provider: str
    latency_ms: float
