from __future__ import annotations

from datetime import datetime, timezone, UTC
from unittest.mock import MagicMock

from assistant.conversation.prompt_builder import build_prompt
from assistant.retrieval.schemas import RetrievalItem, SourceAttribution


def _make_retrieval_item(snippet: str) -> RetrievalItem:
    source = SourceAttribution(
        memory_id="id-1",
        source_type="conversation",
        title="",
        snippet=snippet,
        created_at=datetime.now(UTC),
    )
    return RetrievalItem(memory_id="id-1", score=0.9, snippet=snippet, source=source)


def test_prompt_contains_user_message():
    prompt = build_prompt("Hello?", [], [])
    assert "Hello?" in prompt


def test_prompt_contains_context_when_provided():
    item = _make_retrieval_item("some relevant context")
    prompt = build_prompt("question", [], [item])
    assert "some relevant context" in prompt


def test_prompt_no_context_section_when_empty():
    prompt = build_prompt("question", [], [])
    assert "Retrieved Context" not in prompt


def test_prompt_includes_history():
    msg = MagicMock()
    msg.role = "user"
    msg.content = "Previous question"

    prompt = build_prompt("new question", [msg], [])
    assert "Previous question" in prompt


def test_prompt_with_context_and_history():
    msg = MagicMock()
    msg.role = "assistant"
    msg.content = "Previous answer"

    item = _make_retrieval_item("context chunk")
    prompt = build_prompt("next question", [msg], [item])

    assert "context chunk" in prompt
    assert "Previous answer" in prompt
    assert "next question" in prompt
