from __future__ import annotations

from assistant.policy.guard import PolicyContext, evaluate


async def test_clean_content_allowed_remote():
    decision = await evaluate("What is the weather today?", PolicyContext())
    assert decision.allowed_remote is True
    assert decision.sensitivity_class == "clean"
    assert decision.blocked_patterns == []


async def test_sensitive_content_blocked():
    decision = await evaluate(
        "My API key is sk-abc123XYZabc123XYZabc1234", PolicyContext()
    )
    assert decision.allowed_remote is False
    assert decision.sensitivity_class == "sensitive"
    assert len(decision.blocked_patterns) > 0


async def test_revoked_consent_blocks():
    decision = await evaluate(
        "Normal text",
        PolicyContext(consent_granted=False),
    )
    assert decision.allowed_remote is False
    assert decision.sensitivity_class == "consent_revoked"


async def test_password_detected():
    decision = await evaluate("password=secretvalue", PolicyContext())
    assert decision.allowed_remote is False
    assert "password_kv" in decision.blocked_patterns
