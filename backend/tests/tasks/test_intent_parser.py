from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from assistant.config import Settings
from assistant.tasks.intent_parser import parse_task_intent


@pytest.fixture(autouse=True)
def reset_circuit_breaker():
    from assistant.routing import router
    router._azure_cb._failures.clear()
    yield
    router._azure_cb._failures.clear()


async def test_parse_task_intent_success():
    settings = Settings(routing_preference="ollama")
    response_json = json.dumps({
        "objective": "Send weekly report",
        "due_context": "Friday",
        "impact_level": "normal",
    })

    with patch(
        "assistant.routing.providers.ollama.complete",
        new=AsyncMock(return_value=(response_json, 10.0)),
    ):
        result = await parse_task_intent("Please send the weekly report by Friday", settings)

    assert result is not None
    assert result.objective == "Send weekly report"
    assert result.due_context == "Friday"
    assert result.impact_level == "normal"


async def test_parse_non_task_message_returns_none():
    settings = Settings(routing_preference="ollama")
    result = await parse_task_intent("What is the weather today?", settings)
    assert result is None


async def test_parse_high_impact_task():
    settings = Settings(routing_preference="ollama")
    response_json = json.dumps({
        "objective": "Delete all old records",
        "due_context": None,
        "impact_level": "high",
    })

    with patch(
        "assistant.routing.providers.ollama.complete",
        new=AsyncMock(return_value=(response_json, 10.0)),
    ):
        result = await parse_task_intent("Please delete all old records", settings)

    assert result is not None
    assert result.impact_level == "high"


async def test_parse_invalid_json_returns_none():
    settings = Settings(routing_preference="ollama")

    with patch(
        "assistant.routing.providers.ollama.complete",
        new=AsyncMock(return_value=("not json", 5.0)),
    ):
        result = await parse_task_intent("Please do something", settings)

    assert result is None
