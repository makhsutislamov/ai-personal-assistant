from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from app.agents.base import AgentMetadata, AgentResult, BaseAgent
from app.agents.registry import AgentRegistry
from app.core.orchestrator import Orchestrator
from app.core.session import SessionStore
from app.llm.base import BaseLLMProvider
from app.models.schemas import (
    AgentResultEvent,
    AgentStatusEvent,
    ChatMessage,
    DoneEvent,
    TokenEvent,
    ToolCall,
)

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


class MockLLMProvider(BaseLLMProvider):
    def __init__(self, chat_response: ChatMessage, stream_tokens: list[str] | None = None):
        self._chat_response = chat_response
        self._stream_tokens = stream_tokens or []

    async def chat_completion(self, messages, tools=None) -> ChatMessage:
        return self._chat_response

    async def chat_completion_stream(self, messages, tools=None) -> AsyncIterator[str]:
        tokens = self._stream_tokens

        async def _gen():
            for t in tokens:
                yield t

        return _gen()

    async def health_check(self) -> bool:
        return True


class MockFileAgent(BaseAgent):
    def __init__(self, result_data=None):
        self._result_data = result_data or {"files": []}

    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            name="file_search",
            description="Search files",
            parameters_schema={
                "type": "object",
                "properties": {"pattern": {"type": "string"}},
                "required": ["pattern"],
            },
        )

    async def execute(self, parameters) -> AgentResult:
        return AgentResult(success=True, data=self._result_data, summary="Found files")


async def collect_events(gen) -> list:
    events = []
    async for event in gen:
        events.append(event)
    return events


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestOrchestrator:
    @pytest.fixture
    def session_store(self):
        store = SessionStore()
        return store

    @pytest.fixture
    def registry(self):
        return AgentRegistry()

    @pytest.mark.asyncio
    async def test_direct_response_yields_token_events(self, session_store, registry):
        # content=None triggers the streaming path in _stream_direct so both tokens flow through
        provider = MockLLMProvider(
            chat_response=ChatMessage(role="assistant", content=None),
            stream_tokens=["Hello", " world"],
        )
        orch = Orchestrator(provider, registry, session_store)
        session_id = session_store.create_session()

        gen = await orch.handle_message(session_id, "Hi")
        events = await collect_events(gen)

        token_events = [e for e in events if isinstance(e, TokenEvent)]
        done_events = [e for e in events if isinstance(e, DoneEvent)]
        assert len(token_events) == 2
        assert token_events[0].content == "Hello"
        assert token_events[1].content == " world"
        assert len(done_events) == 1

    @pytest.mark.asyncio
    async def test_tool_call_delegation(self, session_store, registry):
        file_data = {"files": [{"name": "test.py", "path": "/tmp/test.py"}]}
        registry.register(MockFileAgent(result_data=file_data))

        tool_call = ToolCall(
            id="call_001",
            function={"name": "file_search", "arguments": '{"pattern": "*.py"}'},
        )
        first_response = ChatMessage(role="assistant", content=None, tool_calls=[tool_call])

        call_count = 0

        async def side_effect(messages, tools=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return first_response
            return ChatMessage(role="assistant", content="Found 1 Python file.")

        provider = MockLLMProvider(
            chat_response=first_response,
            stream_tokens=["Found 1 Python file."],
        )
        provider.chat_completion = side_effect
        orch = Orchestrator(provider, registry, session_store)
        session_id = session_store.create_session()

        gen = await orch.handle_message(session_id, "Find python files")
        events = await collect_events(gen)

        agent_events = [e for e in events if isinstance(e, AgentStatusEvent)]
        result_events = [e for e in events if isinstance(e, AgentResultEvent)]
        token_events = [e for e in events if isinstance(e, TokenEvent)]
        done_events = [e for e in events if isinstance(e, DoneEvent)]

        assert any(e.status == "working" for e in agent_events)
        assert any(e.status == "complete" for e in agent_events)
        assert len(result_events) == 1
        assert result_events[0].data == file_data
        # Synthesis result yielded as single token from _stream_direct
        assert len(token_events) == 1
        assert len(done_events) == 1

    @pytest.mark.asyncio
    async def test_session_history_appended(self, session_store, registry):
        provider = MockLLMProvider(
            chat_response=ChatMessage(role="assistant", content="Reply"),
            stream_tokens=["Reply"],
        )
        orch = Orchestrator(provider, registry, session_store)
        session_id = session_store.create_session()

        gen = await orch.handle_message(session_id, "Question")
        await collect_events(gen)

        history = session_store.get_history(session_id)
        roles = [m.role for m in history]
        assert "user" in roles
        assert "assistant" in roles

    @pytest.mark.asyncio
    async def test_unknown_tool_call_handled_gracefully(self, session_store, registry):
        tool_call = ToolCall(
            id="call_002",
            function={"name": "nonexistent_tool", "arguments": "{}"},
        )
        first_response = ChatMessage(role="assistant", content=None, tool_calls=[tool_call])

        call_count = 0

        async def side_effect(messages, tools=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return first_response
            return ChatMessage(role="assistant", content="I couldn't complete that.")

        provider = MockLLMProvider(
            chat_response=first_response,
            stream_tokens=["I couldn't complete that."],
        )
        provider.chat_completion = side_effect
        orch = Orchestrator(provider, registry, session_store)
        session_id = session_store.create_session()

        gen = await orch.handle_message(session_id, "Do something unknown")
        events = await collect_events(gen)

        error_status_events = [
            e for e in events if isinstance(e, AgentStatusEvent) and e.status == "error"
        ]
        assert len(error_status_events) == 1
        # Should still finish with DoneEvent
        assert any(isinstance(e, DoneEvent) for e in events)

    @pytest.mark.asyncio
    async def test_done_event_always_emitted(self, session_store, registry):
        provider = MockLLMProvider(
            chat_response=ChatMessage(role="assistant", content=""),
            stream_tokens=[],
        )
        orch = Orchestrator(provider, registry, session_store)
        session_id = session_store.create_session()

        gen = await orch.handle_message(session_id, "Hi")
        events = await collect_events(gen)

        assert any(isinstance(e, DoneEvent) for e in events)

    @pytest.mark.asyncio
    async def test_tool_chain_two_turns(self, session_store, registry):
        """LLM calls tool in turn 1, then answers directly in turn 2 — loop exits cleanly."""
        file_data = {"files": [{"name": "notes.txt", "path": "/home/notes.txt"}]}
        registry.register(MockFileAgent(result_data=file_data))

        tool_call = ToolCall(
            id="call_001",
            function={"name": "file_search", "arguments": '{"pattern": "notes.txt"}'},
        )

        call_count = 0

        async def side_effect(messages, tools=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return ChatMessage(role="assistant", content=None, tool_calls=[tool_call])
            return ChatMessage(role="assistant", content="Here is the file.")

        provider = MockLLMProvider(
            chat_response=ChatMessage(role="assistant", content=None, tool_calls=[tool_call]),
            stream_tokens=["Here is the file."],
        )
        provider.chat_completion = side_effect

        orch = Orchestrator(provider, registry, session_store)
        session_id = session_store.create_session()
        gen = await orch.handle_message(session_id, "find notes.txt")
        events = await collect_events(gen)

        status_events = [e for e in events if isinstance(e, AgentStatusEvent)]
        assert any(e.status == "complete" for e in status_events)
        # First call: tool detection; second call: re-call after tool result
        assert call_count == 2
        assert any(isinstance(e, DoneEvent) for e in events)

    @pytest.mark.asyncio
    async def test_max_iterations_guard(self, session_store, registry):
        """Orchestrator stops after _MAX_TOOL_ITERATIONS and still emits DoneEvent."""
        from app.core.orchestrator import _MAX_TOOL_ITERATIONS

        tool_call = ToolCall(
            id="call_loop",
            function={"name": "file_search", "arguments": '{"pattern": "*.py"}'},
        )
        registry.register(MockFileAgent())

        call_count = 0

        async def always_tool(messages, tools=None):
            nonlocal call_count
            call_count += 1
            return ChatMessage(role="assistant", content=None, tool_calls=[tool_call])

        provider = MockLLMProvider(
            chat_response=ChatMessage(role="assistant", content=None, tool_calls=[tool_call]),
            stream_tokens=["done"],
        )
        provider.chat_completion = always_tool

        orch = Orchestrator(provider, registry, session_store)
        session_id = session_store.create_session()
        gen = await orch.handle_message(session_id, "keep searching")
        events = await collect_events(gen)

        # Initial detection call + one re-call per iteration = _MAX_TOOL_ITERATIONS + 1 total
        assert call_count == _MAX_TOOL_ITERATIONS + 1
        assert any(isinstance(e, DoneEvent) for e in events)
