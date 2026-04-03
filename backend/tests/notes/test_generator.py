from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from assistant.notes.generator import _parse_notes, generate_notes
from assistant.notes.schemas import GeneratedNotes


def test_parse_valid_json():
    raw = json.dumps({
        "summary": "We discussed the project timeline.",
        "decisions": ["Use Python 3.12"],
        "action_items": ["Write tests"],
        "open_questions": ["What is the deadline?"],
        "suggested_tags": ["project", "planning"],
    })
    notes = _parse_notes(raw)
    assert notes.summary == "We discussed the project timeline."
    assert notes.decisions == ["Use Python 3.12"]
    assert notes.action_items == ["Write tests"]
    assert notes.suggested_tags == ["project", "planning"]


def test_parse_json_with_markdown_fences():
    raw = "```json\n" + json.dumps({
        "summary": "Meeting summary",
        "decisions": [],
        "action_items": [],
        "open_questions": [],
        "suggested_tags": [],
    }) + "\n```"
    notes = _parse_notes(raw)
    assert notes.summary == "Meeting summary"


def test_parse_invalid_json_falls_back():
    notes = _parse_notes("This is not JSON at all — just text.")
    assert len(notes.summary) > 0
    assert notes.decisions == []


def test_parse_missing_fields_defaults_to_empty():
    raw = json.dumps({"summary": "Partial data"})
    notes = _parse_notes(raw)
    assert notes.summary == "Partial data"
    assert notes.decisions == []
    assert notes.action_items == []


async def test_generate_notes_with_populated_session():
    from unittest.mock import MagicMock
    from assistant.config import Settings

    # Mock session with messages
    mock_session = MagicMock()
    settings = Settings(routing_preference="ollama")

    model_json = json.dumps({
        "summary": "Alice and Bob discussed the roadmap.",
        "decisions": ["Ship in Q2"],
        "action_items": ["Update docs"],
        "open_questions": [],
        "suggested_tags": ["roadmap"],
    })

    with patch(
        "assistant.notes.generator.get_history",
        new=AsyncMock(return_value=[
            MagicMock(role="user", content="What is the plan?"),
            MagicMock(role="assistant", content="We'll ship in Q2."),
        ]),
    ), patch(
        "assistant.routing.providers.ollama.complete",
        new=AsyncMock(return_value=(model_json, 20.0)),
    ):
        notes = await generate_notes(mock_session, "session-1", settings)

    assert notes.summary == "Alice and Bob discussed the roadmap."
    assert "Ship in Q2" in notes.decisions


async def test_generate_notes_empty_session():
    from unittest.mock import MagicMock
    from assistant.config import Settings

    mock_session = MagicMock()
    settings = Settings(routing_preference="ollama")

    with patch(
        "assistant.notes.generator.get_history",
        new=AsyncMock(return_value=[]),
    ):
        notes = await generate_notes(mock_session, "empty-session", settings)

    assert "No conversation" in notes.summary
