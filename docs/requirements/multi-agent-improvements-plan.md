# Implementation Plan — Multi-Agent Architecture Improvements

Derived from [multi-agent-improvements.md](./multi-agent-improvements.md).

---

## 1) Goal and Scope

**Target:** Evolve the backend agent infrastructure to support a growing roster of agents reliably. Three concrete changes are in scope:

| Task | Scope |
|---|---|
| Task 1 — System prompt | Already applied. Verify tests pass. |
| Task 2 — ACI tool descriptions | Update `FileSearchAgent.metadata()` with improved description |
| Task 4 — Multi-turn tool loop | Refactor `Orchestrator._handle_tool_calls` to loop up to `_MAX_TOOL_ITERATIONS` |
| Task 5 — Provider injection | No code change required yet; registration convention only, enforced by pattern |

**Out of scope:**
- Adding new agents beyond `FileSearchAgent`
- Frontend changes
- Integration or end-to-end tests
- LLM provider changes

---

## 2) Repository Findings

- **Language/runtime:** Python 3.11+, FastAPI, async/await throughout. Tests use `pytest` + `pytest-asyncio`. Package managed via `pyproject.toml` with a `[dev]` extras group.
- **Agent contract:** `BaseAgent` (abc) in `backend/app/agents/base.py` — two abstract methods: `metadata() → AgentMetadata` and `execute(parameters) → AgentResult`. No constructor signature enforced.
- **Registry:** `AgentRegistry` in `backend/app/agents/registry.py` — dict keyed by `meta.name`. `as_tools()` produces OpenAI function-call format. No provider awareness.
- **Orchestrator:** `backend/app/core/orchestrator.py` — single `_handle_tool_calls` path runs all tool calls in one pass, then calls `_stream_direct` for synthesis. No loop, no iteration cap.
- **LLM provider:** `BaseLLMProvider` abc with `chat_completion` (blocking) and `chat_completion_stream` (streaming). Injected into `Orchestrator.__init__`. Already injected into `Orchestrator` via `main.py` lifespan.
- **Test patterns:** `MockLLMProvider` and `MockFileAgent` in `test_orchestrator.py` stand in for real dependencies. `collect_events()` helper drains async generators. Tests use `@pytest.mark.asyncio`.
- **System prompt:** Updated (Task 1 done) — multi-agent chaining permission and synthesis instructions already applied.

---

## 3) Assumptions and Clarifications

**Assumptions:**
- `_MAX_TOOL_ITERATIONS = 5` is an acceptable default; it can be made configurable later.
- After the iteration cap is hit, the orchestrator proceeds to synthesis with whatever tool results have been collected — it does not error out.
- Task 5 (provider injection) requires no code change in this iteration; the convention is established by example and documented. Actual LLM-powered agents are not being built here.
- Existing `test_orchestrator.py` tests must continue to pass unchanged (backward compatibility requirement for single-turn tool call behavior).

**No blocking clarifications needed.**

---

## 4) Implementation Plan

### Phase 1 — Task 2: Improve `FileSearchAgent` tool description

**Step 1.1 — Update `FileSearchAgent.metadata()` description**

- **File:** `backend/app/agents/file_search.py`
- **Objective:** Replace the current description with one that includes example triggers, output description, and explicit "do NOT use" boundaries.
- **Change:** In `FileSearchAgent.metadata()`, replace the `description` string:

```python
description=(
    "Search the local filesystem for files by name or glob pattern. "
    "Use for requests like: 'find my resume', 'where is config.json', "
    "'list all *.py files in ~/projects', 'search for notes.txt'. "
    "Do NOT call for general questions, greetings, or anything unrelated to locating files. "
    "Do NOT use pattern '*' with directory '/' — require a specific directory for broad patterns. "
    "Returns file name, full path, size in bytes, and last-modified timestamp."
),
```

---

### Phase 2 — Task 4: Multi-turn tool loop with max-iterations guard

**Step 2.1 — Add `_MAX_TOOL_ITERATIONS` constant**

- **File:** `backend/app/core/orchestrator.py`
- **Objective:** Declare the iteration ceiling as a module-level constant above the `Orchestrator` class.
- **Change:** Add after the `logger` line:

```python
_MAX_TOOL_ITERATIONS = 5
```

---

**Step 2.2 — Refactor `_handle_tool_calls` to a multi-turn loop**

- **File:** `backend/app/core/orchestrator.py`
- **Objective:** Replace the single-pass tool execution with a `while` loop that re-calls the LLM after each round of tool calls, stopping when the LLM returns no more tool calls or `_MAX_TOOL_ITERATIONS` is reached.
- **Change:** Replace the body of `_handle_tool_calls` with:

```python
async def _handle_tool_calls(
    self,
    session_id: str,
    response_msg: ChatMessage,
    messages: list[ChatMessage],
) -> AsyncIterator[StreamEvent]:
    tools = self._registry.as_tools()
    iteration = 0

    while response_msg.tool_calls and iteration < _MAX_TOOL_ITERATIONS:
        iteration += 1
        messages = messages + [response_msg]

        for tool_call in response_msg.tool_calls or []:
            tool_name = tool_call.function.get("name", "")
            agent = self._registry.get(tool_name)

            yield AgentStatusEvent(agent_name=tool_name, status="working")

            if agent is None:
                tool_result_msg = ChatMessage(
                    role="tool",
                    content=f"Unknown tool: {tool_name}",
                    tool_call_id=tool_call.id,
                )
                messages = messages + [tool_result_msg]
                yield AgentStatusEvent(agent_name=tool_name, status="error")
                continue

            try:
                args_raw = tool_call.function.get("arguments", "{}")
                parameters = json.loads(args_raw) if isinstance(args_raw, str) else (args_raw or {})

                agent_result = await agent.execute(parameters)

                yield AgentStatusEvent(agent_name=tool_name, status="complete")
                yield AgentResultEvent(agent_name=tool_name, data=agent_result.data)

                tool_result_msg = ChatMessage(
                    role="tool",
                    content=json.dumps(agent_result.data) if agent_result.data else agent_result.summary,
                    tool_call_id=tool_call.id,
                )
                messages = messages + [tool_result_msg]

            except Exception as exc:
                logger.exception("Error executing agent %s", tool_name)
                tool_result_msg = ChatMessage(
                    role="tool",
                    content=f"Error executing {tool_name}: {exc}",
                    tool_call_id=tool_call.id,
                )
                messages = messages + [tool_result_msg]
                yield AgentStatusEvent(agent_name=tool_name, status="error")

        # Re-call LLM — it decides whether to call more tools or synthesize
        response_msg = await self._provider.chat_completion(messages, tools=tools or None)

    if iteration >= _MAX_TOOL_ITERATIONS:
        logger.warning(
            "Max tool iterations (%d) reached for session %s", _MAX_TOOL_ITERATIONS, session_id
        )

    # Synthesis — stream final response (may be direct answer or summary of tool results)
    async for event in self._stream_direct(session_id, messages, response_msg):
        yield event
```

- **Key behavioral change:** The synthesis LLM call is now delegated to `_stream_direct` in all cases via the refactored loop exit. The `response_msg` at loop exit is passed directly — if it already has content (LLM chose to respond without more tools), `_stream_direct` yields it immediately without an extra LLM round-trip (existing behavior preserved).

---

**Step 2.3 — Unit tests for multi-turn loop**

- **File:** `backend/tests/test_orchestrator.py`
- **Add the following test cases:**

```python
@pytest.mark.asyncio
async def test_tool_chain_two_turns(self, session_store, registry):
    """LLM calls tool in turn 1, then answers directly in turn 2."""
    file_data = {"files": [{"name": "notes.txt", "path": "/home/notes.txt"}]}
    registry.register(MockFileAgent(result_data=file_data))

    tool_call = ToolCall(
        id="call_001",
        function={"name": "file_search", "arguments": '{"pattern": "notes.txt"}'},
    )
    # First chat_completion → tool call; second → plain text
    provider = MockLLMProvider(
        chat_response=ChatMessage(role="assistant", content=None, tool_calls=[tool_call]),
        stream_tokens=["Found", " notes.txt"],
    )
    # Override: second call returns plain text
    call_count = 0
    original = provider.chat_completion
    async def side_effect(messages, tools=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return ChatMessage(role="assistant", content=None, tool_calls=[tool_call])
        return ChatMessage(role="assistant", content="Here is the file.")
    provider.chat_completion = side_effect

    orch = Orchestrator(provider, registry, session_store)
    session_id = session_store.create_session()
    gen = await orch.handle_message(session_id, "find notes.txt")
    events = await collect_events(gen)

    status_events = [e for e in events if isinstance(e, AgentStatusEvent)]
    assert any(e.status == "complete" for e in status_events)
    assert call_count == 2  # tool detection + synthesis re-call


@pytest.mark.asyncio
async def test_max_iterations_guard(self, session_store, registry):
    """Orchestrator stops after _MAX_TOOL_ITERATIONS even if LLM keeps requesting tools."""
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

    # Should not loop forever; call_count = _MAX_TOOL_ITERATIONS (detection) + 1 (per loop re-call)
    assert call_count == _MAX_TOOL_ITERATIONS + 1
    done_events = [e for e in events if isinstance(e, DoneEvent)]
    assert len(done_events) == 1
```

- **Verification:** `python -m pytest backend/tests/test_orchestrator.py -v`

---

### Phase 3 — Task 5: Document provider injection convention

**Step 3.1 — No code change required.** Task 5 is a registration convention, not a structural code change. The pattern is already supported: `registry.register(SomeAgent(provider=provider))` works today because `BaseAgent` imposes no constructor signature. The first LLM-powered agent added to the project will establish the convention in practice.

**Documentation:** The convention is captured in `multi-agent-improvements.md` Task 5. No additional code or docstrings needed at this stage.

---

## 5) Dependencies and Sequencing

```
Phase 1 (Task 2)   ──► independent, can be done first or in parallel with Phase 2
Phase 2 (Task 4)   ──► depends on nothing; Step 2.3 tests depend on Step 2.2
Phase 3 (Task 5)   ──► no code; can be noted at any point
```

**Parallelizable:** Phase 1 and Phase 2 Steps 2.1–2.2 are fully independent. Tests (Steps 1.1 test + 2.3) should be written alongside their respective implementation steps, not after.

---

## 6) Risks and Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Multi-turn loop changes synthesis behavior for existing single-tool tests | Medium | `_stream_direct` receives `response_msg` from the loop exit — same as before for single-turn. Existing tests must pass without modification. Run `test_orchestrator.py` after Step 2.2. |
| `_stream_direct` called with a `response_msg` that has `tool_calls` set (from last loop re-call returning tools when cap hit) | Low | After cap is hit, the final `response_msg` may still have `tool_calls`. `_stream_direct` only uses `response_msg.content`; tool_calls are ignored. Verify `_stream_direct` does not branch on `tool_calls`. |
| LLM re-call cost: extra LLM call per tool iteration | Known trade-off | Acceptable; aligns with Anthropic's orchestrator-workers pattern. Document in code comment. |
| Session history grows with multi-turn tool messages | Low | `messages` list is built per-request (not persisted mid-turn); only final assistant message is saved to `SessionStore`. No change needed. |

---

## 7) Validation Strategy

### Unit tests
- Run full test suite: `python -m pytest backend/tests/ -v`
- Specific targets:
  - `test_orchestrator.py` — two-turn chain test, max-iterations guard test (Step 2.3)
  - `test_agent_registry.py` — existing `as_tools` format tests must still pass

### Static checks
```bash
# From repo root with venv active
python -m mypy backend/app/core/orchestrator.py backend/app/agents/
python -m ruff check backend/app/
```

### Manual verification
1. Start backend: `uvicorn app.main:create_app --factory --reload`
2. Connect WebSocket to `/ws/chat`, send a file-search request
3. Verify `AgentStatusEvent` stream: `working → complete` sequence appears
4. Verify no behavioral regression for conversational (non-tool) messages

---

## 8) Definition of Done

- [x] `FileSearchAgent.metadata().description` includes example triggers, output description, and "do NOT" boundaries
- [x] `_MAX_TOOL_ITERATIONS = 5` constant defined in `orchestrator.py`
- [x] `_handle_tool_calls` loops up to `_MAX_TOOL_ITERATIONS`, re-calling LLM after each round
- [x] Warning logged when iteration cap is reached
- [x] All existing `test_orchestrator.py` and `test_agent_registry.py` tests pass without modification
- [x] Two new orchestrator tests added: multi-turn chain and max-iterations guard
- [x] One new file-search description assertion test added
- [x] `python -m pytest backend/tests/ -v` exits with code 0
- [x] No new mypy or ruff errors introduced
