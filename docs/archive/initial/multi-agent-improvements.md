# Multi-Agent Architecture Improvements

Improvements based on Anthropic's [Building Effective Agents](https://www.anthropic.com/research/building-effective-agents) best practices, identified in preparation for expanding the agent roster.

---

## Task 1 — Remove system prompt duplication

**File:** `backend/app/core/orchestrator.py`

The tool-guard instructions ("only call a tool when explicitly asked") are currently duplicated in both `_SYSTEM_PROMPT` and each agent's `metadata().description`. Per Anthropic's ACI guidance, invocation guards belong exclusively in the tool description. Duplication produces conflicting signals as more agents are added.

**Change:** Replace the single-tool-focused prompt with a multi-agent-aware system prompt. Move tool invocation guards into each agent's own description (ACI). Add explicit chaining permission, pre-tool reasoning, failure handling, and generic synthesis guidance.

```python
_SYSTEM_PROMPT = """You are a helpful personal AI assistant running on the user's desktop.
You have access to a set of tools that can interact with the user's system and retrieve information on their behalf.

## Tool use
- Before selecting a tool, reason briefly about which tool best matches the user's request.
- You may call multiple tools in sequence if the task requires it (e.g., search for a file, then read its contents).
- Each tool's description specifies exactly when to use it — follow those boundaries strictly.
- If a tool returns an error or empty results, explain what happened and suggest what the user could try instead.
- Never invoke a tool speculatively or to satisfy curiosity — only when the user's request clearly requires it.

## Responses
- After using tools, synthesize the results into a clear, direct answer — don't just dump raw data.
- Use markdown formatting (tables, bullet lists, code blocks) where it aids readability.
- For conversational messages, general questions, or anything not requiring system access, respond directly without invoking any tools."""
```

---

## Task 2 — Improve tool descriptions (ACI investment)

**File:** `backend/app/agents/file_search.py` (and every future agent)

Anthropic recommends treating tool descriptions like docstrings for a junior developer — include example inputs, output shape, and explicit boundaries from other similar tools. This is critical when multiple agents exist so the LLM picks the right one.

**Change:** Enrich each agent's `metadata().description` with:
- Concrete example user phrases that should trigger the tool
- What the tool returns
- Explicit "do NOT use for" boundaries relative to other tools

```python
# Example for FileSearchAgent
description=(
    "Search the local filesystem for files by name or glob pattern. "
    "Use for requests like: 'find my resume', 'where is config.json', 'list all *.py files in ~/projects'. "
    "Do NOT call for general questions, greetings, or anything unrelated to locating files. "
    "Do NOT call with the pattern '*' and directory '/' — require a specific directory for broad patterns. "
    "Returns file name, full path, size in bytes, and last-modified timestamp."
)
```

---

## Task 4 — Multi-turn tool loop with max-iterations guard

**File:** `backend/app/core/orchestrator.py`

Currently the orchestrator handles exactly one round of tool calls and then forces a synthesis response. This blocks real agent chaining (e.g., search → read → summarize). Anthropic explicitly recommends stopping conditions for agentic loops.

**Change:** Convert `_handle_tool_calls` to a loop that re-calls the LLM after each tool round, up to `_MAX_TOOL_ITERATIONS`, allowing the LLM to decide when it has enough information to produce a final answer.

```python
_MAX_TOOL_ITERATIONS = 5

async def _handle_tool_calls(self, session_id, response_msg, messages):
    tools = self._registry.as_tools()
    iteration = 0

    while response_msg.tool_calls and iteration < _MAX_TOOL_ITERATIONS:
        iteration += 1
        messages = messages + [response_msg]

        for tool_call in response_msg.tool_calls:
            # ... existing per-tool dispatch and result appending ...

        # Re-call LLM to decide next action or produce final answer
        response_msg = await self._provider.chat_completion(messages, tools=tools or None)

    if iteration >= _MAX_TOOL_ITERATIONS:
        logger.warning("Max tool iterations (%d) reached for session %s", _MAX_TOOL_ITERATIONS, session_id)

    # Synthesis stream
    async for event in self._stream_direct(session_id, messages, response_msg):
        yield event
```

---

## Task 5 — Provider injection for LLM-powered agents

**File:** `backend/app/main.py`, `backend/app/agents/base.py`

When agents that require their own internal reasoning loop are added (e.g., `ResearchAgent`, `CodingAgent`), they need access to an LLM provider. This should be injected at registration time — not resolved inside the agent — so that:

- Different agents can use different models (cheaper model for simple agents, capable model for reasoning agents)
- Agents remain testable in isolation
- The orchestrator and registry require no changes

**Change:** Pass the provider (or a factory callable) to agents that need it at `registry.register()` time in `lifespan`:

```python
# main.py — lifespan
registry.register(FileSearchAgent())                          # deterministic, no LLM
registry.register(ResearchAgent(provider=provider))           # LLM-powered, same provider
registry.register(SomeAgent(provider=create_provider(...)))   # LLM-powered, different model
```

Each LLM-powered agent implements its own internal loop inside `execute()` and still returns a plain `AgentResult` — the orchestrator remains unchanged.

---

## Decision rule for new agents

```
New agent needed?
    │
    ├── Can the task be fully expressed as a deterministic function of its inputs?
    │       └── YES → plain code agent (Tasks 1–4 apply)
    │
    └── Does the agent need to observe intermediate results and change course?
            └── YES → LLM-powered agent with internal loop (Task 5 applies)
                       still implements BaseAgent; orchestrator unchanged
```
