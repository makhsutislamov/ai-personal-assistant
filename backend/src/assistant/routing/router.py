from __future__ import annotations

import time
import uuid
from collections import deque

from assistant.config import Settings
from assistant.policy.guard import PolicyDecision
from assistant.routing.schemas import ModelResponse
from assistant.telemetry.setup import get_meter, get_tracer

_tracer = get_tracer("routing")
_meter = get_meter("routing")
_routing_decisions = _meter.create_counter(
    "assistant.routing.decisions",
    description="Count of routing decisions by provider and sensitivity class",
)

# Circuit breaker config
_CB_FAILURE_THRESHOLD = 3
_CB_WINDOW_SECONDS = 60


class _CircuitBreaker:
    def __init__(self, threshold: int = _CB_FAILURE_THRESHOLD, window: float = _CB_WINDOW_SECONDS):
        self._threshold = threshold
        self._window = window
        self._failures: deque[float] = deque()

    def record_failure(self) -> None:
        now = time.monotonic()
        self._failures.append(now)
        self._prune(now)

    def record_success(self) -> None:
        self._failures.clear()

    def is_open(self) -> bool:
        self._prune(time.monotonic())
        return len(self._failures) >= self._threshold

    def _prune(self, now: float) -> None:
        while self._failures and self._failures[0] < now - self._window:
            self._failures.popleft()


_azure_cb = _CircuitBreaker()


async def invoke(
    prompt: str,
    policy_decision: PolicyDecision,
    settings: Settings,
    request_id: str | None = None,
) -> ModelResponse:
    """Route prompt to the appropriate model provider."""
    from assistant.routing.providers import azure_openai_provider
    from assistant.routing.providers import ollama as ollama_provider

    if request_id is None:
        request_id = str(uuid.uuid4())

    use_ollama = (
        not policy_decision.allowed_remote
        or settings.routing_preference == "ollama"
        or _azure_cb.is_open()
    )

    if use_ollama:
        try:
            text, latency_ms = await ollama_provider.complete(prompt)
            provider = "ollama"
            model_used = "llama3"
        except Exception:
            raise
    else:
        try:
            text, latency_ms = await azure_openai_provider.complete(
                prompt=prompt,
                endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_api_key,
                deployment=settings.azure_openai_deployment,
                api_version=settings.azure_openai_api_version,
            )
            _azure_cb.record_success()
            provider = "azure_openai"
            model_used = settings.azure_openai_deployment or "azure_openai"
        except Exception:
            _azure_cb.record_failure()
            if _azure_cb.is_open():
                # Fallback to Ollama
                text, latency_ms = await ollama_provider.complete(prompt)
                provider = "ollama"
                model_used = "llama3"
            else:
                raise

    _routing_decisions.add(
        1,
        {
            "provider": provider,
            "sensitivity_class": policy_decision.sensitivity_class,
        },
    )
    return ModelResponse(
        text=text,
        model_used=model_used,
        provider=provider,
        latency_ms=latency_ms,
    )
