# AI Personal Assistant — Copilot Instructions

A cross-platform desktop AI chat application built as a three-layer Electron app: React frontend ↔ Python/FastAPI backend ↔ Electron shell.

## Architecture

```
Electron (main.ts)          — Spawns Python backend, manages window, generates auth token
  └── React Frontend        — Chat UI on port 5173 (dev), WebSocket streaming
  └── Python Backend        — FastAPI on dynamic port, orchestrates LLM + agent execution
```

**Key directories:**
- `backend/app/agents/` — Agent implementations (subclass `BaseAgent`)
- `backend/app/core/orchestrator.py` — LLM call loop, tool dispatch, stream event emission
- `backend/app/llm/` — Provider abstraction (Ollama, Azure OpenAI)
- `frontend/src/components/` — React UI components
- `frontend/src/types/index.ts` — Shared TypeScript interfaces (single source of truth)

## Build & Test

```bash
# Install all dependencies
npm install && cd frontend && npm install && cd ..
cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -e '.[dev]'

# Run in dev mode (all three processes)
./scripts/dev.sh

# Tests
npm run test:backend      # pytest (backend/tests/)
npm run test:frontend     # Vitest (frontend/src/**/__tests__/)

# Full production build
npm run build
```

> macOS Homebrew Python blocks global pip (PEP 668). Always use `backend/.venv`.

## Python Conventions

- `from __future__ import annotations` at the top of every file
- Async-first: prefer `async def`; use `asyncio.to_thread()` for sync I/O
- Type hints required; line length 100 (ruff enforced)
- `logging.getLogger(__name__)` — never `print()`
- Config persists via `platformdirs` to `~/.config/ai-personal-assistant/settings.json`

## TypeScript/React Conventions

- All shared types in `frontend/src/types/index.ts` — don't define types inline in components
- Hooks in `frontend/src/hooks/`, colocated `__tests__/` subdirectory
- Tailwind utility classes only — no inline styles, no CSS modules
- React Markdown + remark-gfm for all assistant message rendering

## Adding a New Agent

1. Create `backend/app/agents/<name>.py`, subclass `BaseAgent`:
   ```python
   from __future__ import annotations
   from app.agents.base import BaseAgent, AgentMetadata

   class MyAgent(BaseAgent):
       def metadata(self) -> AgentMetadata:
           return AgentMetadata(name="my_agent", description="...", tools=[...])

       async def execute(self, args: dict) -> dict:
           ...
   ```
2. Register in `backend/app/main.py` startup: `registry.register(MyAgent())`
3. Add tests in `backend/tests/test_<name>.py`

## WebSocket Stream Events

The orchestrator emits a discriminated union on `type`:

| `type` | Payload | Purpose |
|--------|---------|---------|
| `token` | `content: str` | Streamed LLM text |
| `agent_status` | `agent_name`, `status` | "working" / "done" |
| `agent_result` | `agent_name`, `data` | Structured agent output |
| `done` | — | End of response |
| `error` | `message: str` | Fatal error |

## REST API (Backend)

- `GET /api/health`
- `GET/PUT /api/settings` — LLM provider config; PUT reloads the provider immediately
- `POST /api/sessions` → returns session UUID
- `GET /api/settings/providers/status` — health checks for Ollama + Azure OpenAI
- `WS /ws/chat?token=<auth>` — main streaming endpoint

Auth: Electron generates a 32-byte hex token at startup; WebSocket closes with `4001` if invalid.

## LLM Providers

Switch provider via settings UI or `settings.json`. The factory in `backend/app/llm/factory.py` recreates the instance on every settings update. Supported: **Ollama** (local, `http://localhost:11434`) and **Azure OpenAI**.

## Common Pitfalls

- **Backend port is dynamic** — Electron reads it from stdout; never hardcode it in frontend
- **macOS file search** — `_MACOS_SKIP_DIRS` frozenset prevents infinite loops in System Volumes
- **Tool call args** — Orchestrator accepts both string-encoded JSON and dict; handle both when extending
- **WebSocket retries cap at 5** — Frontend does not auto-recover after 5 failures; requires app restart
- **Session state is ephemeral** — No persistence in MVP; conversation history clears on app close
