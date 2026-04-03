from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from assistant.policy.detector import SensitiveMatch, detect_sensitive
from assistant.telemetry.setup import get_tracer

_tracer = get_tracer("policy")


@dataclass
class PolicyContext:
    source_type: str = "conversation"
    consent_granted: bool = True


@dataclass
class PolicyDecision:
    allowed_remote: bool
    sensitivity_class: str
    reason: str
    blocked_patterns: list[str] = field(default_factory=list)


async def evaluate(content: str, context: PolicyContext) -> PolicyDecision:
    """Evaluate whether content may be sent to a remote model."""
    with _tracer.start_as_current_span("policy.evaluate") as span:
        span.set_attribute("source_type", context.source_type)
        decision = await _evaluate(content, context)
        span.set_attribute("sensitivity_class", decision.sensitivity_class)
        span.set_attribute("allowed_remote", decision.allowed_remote)
        return decision


async def _evaluate(content: str, context: PolicyContext) -> PolicyDecision:
    if not context.consent_granted:
        return PolicyDecision(
            allowed_remote=False,
            sensitivity_class="consent_revoked",
            reason="Source consent has been revoked",
        )

    matches = detect_sensitive(content)
    if matches:
        return PolicyDecision(
            allowed_remote=False,
            sensitivity_class="sensitive",
            reason="Sensitive content detected; routing to local model only",
            blocked_patterns=[m.label for m in matches],
        )

    return PolicyDecision(
        allowed_remote=True,
        sensitivity_class="clean",
        reason="No sensitive content detected",
    )
