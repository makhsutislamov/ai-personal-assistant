# AI Personal Assistant — Implementation Plan

## 1) Goal and Scope

**Target:** Build the MVP of a macOS desktop AI personal assistant with a conversational chat UI, file search agent, and configurable LLM backend (Ollama / Azure OpenAI).

**In-Scope (MVP):**
- Python FastAPI backend with WebSocket streaming, orchestrator, agent framework, file search agent, LLM provider abstraction (Ollama + Azure OpenAI), settings management
- React + TypeScript frontend with chat UI, markdown rendering, agent status indicators, settings panel
- Electron shell with Python backend lifecycle management
- macOS packaging (.dmg)
- Unit tests for all backend and frontend modules

**Out-of-Scope:**
- Conversation persistence across sessions (Iteration 2)
- Additional agents beyond file search
- File content search
- Integration tests
- Telemetry / analytics
- OS keychain credential storage (future improvement)

---

## 2) Repository Findings

- **Greenfield project** — repository contains only `docs/` (business requirements, solution design) and `.github/` (prompts, agents). No application code exists.
- **Existing `.venv`** at `backend/.venv` indicates Python virtual environment convention is established.
- **Stack defined in solution design:** Electron + React/TypeScript frontend, Python FastAPI backend, local HTTP + WebSocket IPC.
- **Project layout defined** in solution design Section 10.3 — follow exactly.
- No CI pipeline, no `package.json`, no `pyproject.toml` exist yet.

---

## 3) Assumptions and Clarifications

**Assumptions:**
- Python 3.11+ is available on the development machine (confirmed: venv already exists).
- Node.js 20 LTS+ is available for Electron and frontend development.
- Target platform is macOS only; Windows/Linux deferred to a future iteration.
- The backend binds to `127.0.0.1` only, with a per-launch shared secret token.
- Settings stored as JSON via `platformdirs` for path resolution.
- Ollama models with tool-calling support (Llama 3.1 8B+) are recommended; fallback prompt-based intent detection is included.

**Clarifications Needed:**
- None — the business requirements and solution design are sufficiently detailed to proceed.

---

## 4) Implementation Plan

### Phase 1 — Backend Foundation

#### Step 1.1: Python Project Scaffold

**Objective:** Create the backend project structure with dependency management.

**Changes:**
- Create `backend/pyproject.toml` with project metadata and dependencies
- Create `backend/app/__init__.py` (empty package init)
- Create directory structure: `backend/app/{api,core,agents,llm,models}/` with `__init__.py` in each
- Create `backend/tests/__init__.py`

**Dependencies (pyproject.toml):**
```toml
[project]
name = "ai-personal-assistant-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.128.0",
    "uvicorn[standard]>=0.34.0",
    "websockets>=14.2",
    "openai>=2.11.0",
    "ollama>=0.4.8",
    "platformdirs>=4.3.6",
    "pydantic>=2.11.1",
    "pydantic-settings>=2.8.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.5",
    "pytest-asyncio>=1.0.0",
    "httpx>=0.28.1",
    "ruff>=0.11.6",
    "mypy>=1.15.0",
]
```

**Execution:**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

**Unit Tests:** N/A (scaffold only)

**Verification:** `python -c "import fastapi; print(fastapi.__version__)"` succeeds.

---

#### Step 1.2: Pydantic Models and Schemas

**Objective:** Define all API data models used across the backend.

**Create `backend/app/models/schemas.py`:**
- `ChatMessage` (role, content, tool_calls, tool_call_id)
- `UserMessagePayload` (type, session_id, content)
- `StreamEvent` (type, content/agent_name/status/data/code/message — discriminated union)
- `SettingsSchema` (llm_provider, ollama config, azure_openai config)
- `OllamaSettings` (base_url, model)
- `AzureOpenAISettings` (endpoint, api_key, deployment, api_version)
- `ProviderStatus` (available, models)
- `SessionResponse` (session_id)

**Unit Tests (`backend/tests/test_schemas.py`):**
- Validate `SettingsSchema` round-trips to/from JSON
- Validate `UserMessagePayload` rejects missing fields
- Validate `ChatMessage` with and without tool_calls

**Verification:** `pytest backend/tests/test_schemas.py` passes.

---

#### Step 1.3: Configuration Manager

**Objective:** Load/save user settings to a local JSON file with cross-platform path resolution.

**Create `backend/app/core/config.py`:**
- `ConfigManager` class:
  - `__init__()` — resolves settings path via `platformdirs.user_config_dir("ai-personal-assistant")`
  - `load() -> SettingsSchema` — reads JSON, returns defaults if file missing
  - `save(settings: SettingsSchema) -> None` — writes JSON with `0o600` file permissions
  - `get_settings_path() -> Path`
- Default settings: `llm_provider="ollama"`, `ollama.base_url="http://localhost:11434"`, `ollama.model="llama3.1"`

**Unit Tests (`backend/tests/test_config.py`):**
- `test_load_defaults_when_no_file` — returns default settings
- `test_save_and_load_roundtrip` — save settings, load them back, verify equality
- `test_file_permissions` — verify saved file has `0o600` permissions
- Use `tmp_path` fixture for isolated file system

**Verification:** `pytest backend/tests/test_config.py` passes.

---

#### Step 1.4: LLM Provider Abstraction

**Objective:** Implement the strategy-pattern LLM provider interface with Ollama and Azure OpenAI implementations.

**Create `backend/app/llm/base.py`:**
- `BaseLLMProvider` ABC with methods:
  - `async chat_completion_stream(messages, tools) -> AsyncIterator[str]`
  - `async chat_completion(messages, tools) -> ChatMessage`
  - `async health_check() -> bool`

**Create `backend/app/llm/ollama_provider.py`:**
- `OllamaProvider(BaseLLMProvider)`:
  - `__init__(settings: OllamaSettings)` — creates `ollama.AsyncClient(host=settings.base_url)`
  - `chat_completion_stream` — calls `client.chat(model=..., messages=..., tools=..., stream=True)`, yields `part['message']['content']`
  - `chat_completion` — calls `client.chat(model=..., messages=..., tools=...)`, returns `ChatMessage`
  - `health_check` — calls `client.list()`, returns `True` on success, `False` on connection error

**Create `backend/app/llm/azure_openai_provider.py`:**
- `AzureOpenAIProvider(BaseLLMProvider)`:
  - `__init__(settings: AzureOpenAISettings)` — creates `openai.AsyncAzureOpenAI(azure_endpoint=..., api_key=..., api_version=...)`
  - `chat_completion_stream` — uses `client.chat.completions.create(model=deployment, messages=..., tools=..., stream=True)`, yields `chunk.choices[0].delta.content`
  - `chat_completion` — non-streaming create, returns `ChatMessage`
  - `health_check` — lightweight model list call or completion, returns bool

**Create `backend/app/llm/factory.py`:**
- `create_provider(settings: SettingsSchema) -> BaseLLMProvider` — match on `settings.llm_provider`

**Unit Tests (`backend/tests/test_llm_providers.py`):**
- Mock `ollama.AsyncClient` — test `OllamaProvider.chat_completion_stream` yields tokens
- Mock `ollama.AsyncClient` — test `OllamaProvider.health_check` returns `True`/`False`
- Mock `openai.AsyncAzureOpenAI` — test `AzureOpenAIProvider.chat_completion_stream` yields tokens
- Mock both — test `AzureOpenAIProvider.health_check` error returns `False`
- Test `create_provider` returns correct type for each provider string

**Verification:** `pytest backend/tests/test_llm_providers.py` passes.

---

#### Step 1.5: Session Store

**Objective:** In-memory session management for conversation history.

**Create `backend/app/core/session.py`:**
- `SessionStore` class:
  - `_sessions: dict[str, list[ChatMessage]]`
  - `create_session() -> str` — generates UUID, stores empty list
  - `get_history(session_id: str) -> list[ChatMessage]`
  - `append_message(session_id: str, message: ChatMessage) -> None`
  - `delete_session(session_id: str) -> None`

**Unit Tests (`backend/tests/test_session.py`):**
- `test_create_session` — returns valid UUID
- `test_append_and_get_history` — messages accumulate
- `test_delete_session` — history cleared after deletion
- `test_get_history_invalid_session` — returns empty list or raises

**Verification:** `pytest backend/tests/test_session.py` passes.

---

#### Step 1.6: Agent Framework (Base + Registry)

**Objective:** Define the agent interface and registry for dynamic agent registration.

**Create `backend/app/agents/base.py`:**
- `AgentMetadata` dataclass (name, description, parameters_schema)
- `AgentResult` dataclass (success, data, summary)
- `BaseAgent` ABC with `metadata() -> AgentMetadata` and `async execute(parameters: dict) -> AgentResult`

**Create `backend/app/agents/registry.py`:**
- `AgentRegistry` class:
  - `register(agent: BaseAgent) -> None`
  - `get(name: str) -> BaseAgent | None`
  - `all_metadata() -> list[AgentMetadata]`
  - `as_tools() -> list[dict]` — converts metadata to OpenAI function-calling tool definitions

**Unit Tests (`backend/tests/test_agent_registry.py`):**
- Create a `MockAgent(BaseAgent)` for testing
- `test_register_and_get` — register an agent, retrieve it by name
- `test_all_metadata` — returns list of registered agent metadata
- `test_as_tools` — returns valid OpenAI tool schema format
- `test_get_unregistered` — returns `None`

**Verification:** `pytest backend/tests/test_agent_registry.py` passes.

---

#### Step 1.7: File Search Agent

**Objective:** Implement filesystem search by name/glob pattern.

**Create `backend/app/agents/file_search.py`:**
- `FileSearchAgent(BaseAgent)`:
  - `metadata()` — returns name="File Search", description, parameters_schema (pattern, directory)
  - `async execute(parameters: dict) -> AgentResult`:
    - Wraps `_search()` in `asyncio.to_thread()`
    - `_search(pattern, directory)` — uses `os.scandir()` recursively
    - Matches via `fnmatch.fnmatch()` for glob patterns, case-insensitive substring for plain text
    - Default directory: `/`
    - Catches `PermissionError`, `OSError` per directory — tracks skipped directories
    - Returns `AgentResult` with files list (name, path, last_modified, size_bytes), directories_searched, directories_skipped, skipped_reasons
    - Result limit: 100 files (configurable)
  - macOS-specific:
    - Skip `/System/Volumes/Data` duplicates

**Unit Tests (`backend/tests/test_file_search.py`):**
- `test_search_existing_files` — create temp directory with test files, search by glob, verify results
- `test_search_no_results` — search for non-existent pattern, verify empty results
- `test_search_permission_error` — mock `os.scandir` to raise `PermissionError`, verify graceful handling
- `test_result_limit` — create 150+ files, verify max 100 returned
- `test_metadata_schema` — verify metadata returns valid JSON schema
- Use `tmp_path` fixture for all file system tests

**Verification:** `pytest backend/tests/test_file_search.py` passes.

---

#### Step 1.8: Orchestrator

**Objective:** Central coordination — manages conversation flow, LLM tool calling, agent delegation.

**Create `backend/app/core/orchestrator.py`:**
- `Orchestrator` class:
  - `__init__(provider: BaseLLMProvider, registry: AgentRegistry, session_store: SessionStore)`
  - `async handle_message(session_id: str, content: str) -> AsyncIterator[StreamEvent]`:
    1. Append user message to session history
    2. Build messages array with system prompt + history
    3. Call `provider.chat_completion(messages, tools=registry.as_tools())`
    4. If response contains tool calls:
       - Yield `StreamEvent(type="agent_status", agent_name=..., status="working")`
       - Execute agent via `registry.get(tool_name).execute(params)`
       - Yield `StreamEvent(type="agent_status", agent_name=..., status="complete")`
       - Append tool result to messages, call LLM again for synthesis
       - Stream synthesis response as `StreamEvent(type="token", ...)`
    5. If response is direct text:
       - Stream via `provider.chat_completion_stream(messages)`
       - Yield `StreamEvent(type="token", ...)` for each token
    6. Yield `StreamEvent(type="done")`
    7. Append assistant response to session history
  - System prompt: instructs LLM to use tools when user asks about files, otherwise respond directly
  - Fallback: if tool calling not supported, parse LLM response for JSON-formatted agent invocations

**Unit Tests (`backend/tests/test_orchestrator.py`):**
- Mock `BaseLLMProvider` and `AgentRegistry`
- `test_direct_response` — LLM returns text, verify token StreamEvents + done
- `test_tool_call_delegation` — LLM returns tool_call, verify agent_status events + agent execution + synthesis
- `test_session_history_appended` — verify messages appended to session store
- `test_unknown_tool_call` — LLM calls non-existent tool, verify graceful error

**Verification:** `pytest backend/tests/test_orchestrator.py` passes.

---

#### Step 1.9: FastAPI Application and API Endpoints

**Objective:** Wire up REST and WebSocket endpoints.

**Create `backend/app/main.py`:**
- FastAPI app with `lifespan` context manager:
  - On startup: load config, create provider, create session store, create registry, register FileSearchAgent
  - Store all in `app.state`
- CORS middleware: allow `http://localhost:*`
- Health endpoint: `GET /api/health` → `{"status": "ok"}`

**Create `backend/app/api/chat.py`:**
- `@router.websocket("/ws/chat")`:
  - Validate shared secret token from query param or header
  - Accept connection
  - Loop: receive JSON (`UserMessagePayload`), call `orchestrator.handle_message()`, send each `StreamEvent` as JSON
  - Handle `WebSocketDisconnect` gracefully

**Create `backend/app/api/settings.py`:**
- `GET /api/settings` — return current settings (redact api_key in response)
- `PUT /api/settings` — validate with Pydantic, save via ConfigManager, recreate LLM provider
- `GET /api/settings/providers/status` — call health_check on configured providers, return status

**Create `backend/app/api/sessions.py`:**
- `POST /api/sessions` — create session, return `{ session_id }`
- `DELETE /api/sessions/{session_id}` — delete session

**Unit Tests (`backend/tests/test_api.py`):**
- Use FastAPI `TestClient`
- `test_health_endpoint` — GET /api/health returns 200
- `test_create_session` — POST /api/sessions returns session_id
- `test_delete_session` — DELETE /api/sessions/{id} returns 200
- `test_get_settings` — GET /api/settings returns default settings
- `test_put_settings_valid` — PUT /api/settings updates and returns config
- `test_put_settings_invalid` — PUT /api/settings with bad data returns 422
- `test_websocket_chat` — connect to /ws/chat, send message, receive streaming events (mock LLM provider)

**Verification:** `pytest backend/tests/test_api.py` passes. Manual: `uvicorn app.main:app --reload` starts successfully.

---

### Phase 2 — Frontend Foundation

#### Step 2.1: React + TypeScript Project Scaffold

**Objective:** Create the frontend project with Vite.

**Execution:**
```bash
cd <project-root>
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

**Additional Dependencies:**
```bash
npm install react-markdown remark-gfm react-syntax-highlighter
npm install -D @types/react-syntax-highlighter tailwindcss @tailwindcss/vite
```

**Changes:**
- Update `frontend/vite.config.ts`: add Tailwind CSS plugin, configure dev server port (e.g., 5173)
- Create `frontend/src/index.css` with Tailwind imports (`@import "tailwindcss"`)
- Clean out default Vite template content from `App.tsx`

**Unit Tests:** N/A (scaffold only)

**Verification:** `npm run dev` starts, blank page loads at `http://localhost:5173`.

---

#### Step 2.2: API Service Layer

**Objective:** Create HTTP and WebSocket client helpers for backend communication.

**Create `frontend/src/services/api.ts`:**
- `const BASE_URL` — configurable, defaults to `http://localhost:8000`
- `createSession(): Promise<{ session_id: string }>` — POST /api/sessions
- `deleteSession(sessionId: string): Promise<void>` — DELETE /api/sessions/{id}
- `getSettings(): Promise<Settings>` — GET /api/settings
- `updateSettings(settings: Settings): Promise<Settings>` — PUT /api/settings
- `getProviderStatus(): Promise<ProviderStatus>` — GET /api/settings/providers/status
- `createChatWebSocket(sessionId: string, token: string): WebSocket` — connects to `ws://localhost:8000/ws/chat`

**Create `frontend/src/types/index.ts`:**
- TypeScript interfaces matching backend schemas: `ChatMessage`, `StreamEvent`, `Settings`, `OllamaSettings`, `AzureOpenAISettings`, `ProviderStatus`, `FileResult`

**Unit Tests (`frontend/src/services/__tests__/api.test.ts`):**
- Mock `fetch` — test `createSession` sends correct request, parses response
- Mock `fetch` — test `getSettings` returns typed settings
- Mock `fetch` — test `updateSettings` sends PUT with body

**Verification:** Tests pass with `npm test`.

---

#### Step 2.3: Chat Hook (useChat)

**Objective:** Manage WebSocket connection, message state, and streaming.

**Create `frontend/src/hooks/useChat.ts`:**
- `useChat(backendUrl: string)` hook:
  - State: `messages: Message[]`, `isStreaming: boolean`, `activeAgent: { name: string, status: string } | null`, `error: string | null`, `sessionId: string | null`
  - On mount: call `createSession()`, store session_id
  - `sendMessage(content: string)`: send `UserMessagePayload` via WebSocket
  - WebSocket `onmessage` handler:
    - `token` event → append to current assistant message
    - `agent_status` event → update `activeAgent` state
    - `agent_result` event → store structured data
    - `done` event → finalize message, set `isStreaming = false`
    - `error` event → set `error` state
  - WebSocket reconnection with exponential backoff (max 5 retries)
  - `startNewChat()`: delete current session, create new one, clear messages

**Unit Tests (`frontend/src/hooks/__tests__/useChat.test.ts`):**
- Mock WebSocket — test `sendMessage` sends correct JSON
- Mock WebSocket — test token events accumulate in message content
- Mock WebSocket — test agent_status events update activeAgent
- Mock WebSocket — test done event finalizes message

**Verification:** Tests pass with `npm test`.

---

#### Step 2.4: Settings Hook (useSettings)

**Objective:** Manage settings state and REST communication.

**Create `frontend/src/hooks/useSettings.ts`:**
- `useSettings()` hook:
  - State: `settings: Settings | null`, `providerStatus: ProviderStatus | null`, `loading: boolean`, `error: string | null`
  - `loadSettings()` — GET /api/settings
  - `saveSettings(settings: Settings)` — PUT /api/settings
  - `checkProviderStatus()` — GET /api/settings/providers/status

**Unit Tests (`frontend/src/hooks/__tests__/useSettings.test.ts`):**
- Mock fetch — test `loadSettings` populates state
- Mock fetch — test `saveSettings` sends correct payload

**Verification:** Tests pass with `npm test`.

---

#### Step 2.5: Chat UI Components

**Objective:** Build the chat interface components.

**Create `frontend/src/components/ChatWindow.tsx`:**
- Main container; renders message list + input bar
- Uses `useChat` hook
- Flexbox layout, `max-width: 720px` centered container
- Auto-scrolls to bottom on new messages

**Create `frontend/src/components/MessageBubble.tsx`:**
- Renders individual message (user or assistant)
- User messages: right-aligned, colored background
- Assistant messages: left-aligned, uses `react-markdown` with `remark-gfm` for rendering
- Code blocks use `react-syntax-highlighter`

**Create `frontend/src/components/AgentIndicator.tsx`:**
- Shows "File Search Agent is working…" pill/badge when `activeAgent` is set
- Animated spinner/pulse indicator
- Disappears when agent status is "complete"

**Create `frontend/src/components/InputBar.tsx`:**
- Text input (textarea for multi-line) + Send button
- Fixed to bottom of chat window
- Submit on Enter (Shift+Enter for newline)
- Disabled while `isStreaming` is true
- Auto-focus on mount

**Create `frontend/src/components/Sidebar.tsx`:**
- "New Chat" button — calls `startNewChat()`
- App title/logo area
- Placeholder for future session list

**Update `frontend/src/App.tsx`:**
- Layout: Sidebar + ChatWindow
- Responsive: sidebar collapsible on small screens

**Unit Tests:**
- `MessageBubble.test.tsx` — renders user message, renders markdown in assistant message
- `AgentIndicator.test.tsx` — shows when activeAgent is set, hidden when null
- `InputBar.test.tsx` — calls onSend on Enter, disabled when streaming

**Verification:** `npm run dev` — chat UI renders, manual visual check.

---

#### Step 2.6: Settings Panel

**Objective:** UI for LLM provider configuration.

**Create `frontend/src/components/SettingsPanel.tsx`:**
- Toggle/modal accessible from sidebar or header icon
- Provider selector: radio buttons for "Ollama" / "Azure OpenAI"
- Ollama fields: Base URL, Model name
- Azure OpenAI fields: Endpoint, API Key (password input), Deployment, API Version
- "Test Connection" button — calls `checkProviderStatus()`
- Save button — calls `saveSettings()`
- Status indicators (green/red) for provider availability
- Validation: required fields highlighted if empty

**Unit Tests (`frontend/src/components/__tests__/SettingsPanel.test.tsx`):**
- Renders provider options
- Shows Ollama fields when Ollama selected
- Shows Azure fields when Azure selected
- Calls save callback with correct data

**Verification:** Settings panel opens, fields render, save persists.

---

### Phase 3 — Electron Shell

#### Step 3.1: Electron Project Setup

**Objective:** Create Electron main process that hosts the React frontend and manages the Python backend.

**Create root `package.json`:**
```json
{
  "name": "ai-personal-assistant",
  "version": "0.1.0",
  "private": true,
  "main": "electron/main.js",
  "scripts": {
    "dev:frontend": "cd frontend && npm run dev",
    "dev:backend": "cd backend && .venv/bin/uvicorn app.main:app --reload --host 127.0.0.1",
    "dev:electron": "electron .",
    "build": "npm run build:frontend && npm run build:backend && electron-builder",
    "build:frontend": "cd frontend && npm run build",
    "build:backend": "cd scripts && bash build-backend.sh"
  }
}
```

**Install Electron dependencies at root:**
```bash
npm install --save-dev electron electron-builder typescript @types/node ts-node
```

Electron latest stable: **v35.x** (per Context7 docs, Electron 12+ defaults: `contextIsolation: true`, `nodeIntegration: false`).

**Create `electron/main.ts`:**
- `app.whenReady()` → spawn Python backend, wait for health check, create `BrowserWindow`
- `BrowserWindow` config:
  - `webPreferences: { preload: path.join(__dirname, 'preload.js'), contextIsolation: true, nodeIntegration: false }`
  - `width: 1200, height: 800, minWidth: 400, minHeight: 500`
- In dev mode: load `http://localhost:5173` (Vite dev server)
- In prod mode: load `file://...frontend/dist/index.html`
- Generate per-launch shared secret token, pass to both renderer (via preload) and Python backend (via env var)
- On `window-all-closed` → kill Python process, quit app

**Create `electron/preload.ts`:**
- Use `contextBridge.exposeInMainWorld('electronAPI', { backendPort, authToken })` to pass backend connection info to renderer
- No Node.js APIs exposed beyond these values

**Create `electron/python-manager.ts`:**
- `startPythonBackend()`:
  - Find available TCP port (use `net.createServer` trick)
  - Spawn Python: `child_process.spawn(pythonPath, ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', port])`
  - Pass `AUTH_TOKEN` env var
  - Monitor child process for crashes, restart up to 3 times
- `waitForHealth(port, maxRetries=50, intervalMs=100)` — poll `GET http://127.0.0.1:{port}/api/health`
- `stopPythonBackend()` — send SIGTERM, wait, force kill after timeout

**Unit Tests:** Electron main process testing is complex; defer to manual verification and Phase 4 CI.

**Verification:** `npm run dev:backend` + `npm run dev:frontend` + `npm run dev:electron` — app window opens, chat works end-to-end.

---

#### Step 3.2: Electron Builder Configuration

**Objective:** Configure macOS packaging.

**Create `electron-builder.yml`:**
```yaml
appId: com.ai-personal-assistant.app
productName: AI Personal Assistant
directories:
  output: dist-electron
  buildResources: build
files:
  - electron/**/*
  - frontend/dist/**/*
  - backend/dist/**/*
mac:
  category: public.app-category.productivity
  target:
    - target: dmg
      arch: [x64, arm64]
extraResources:
  - from: backend/dist/
    to: backend/
    filter: ["**/*"]
```

**Create `scripts/build-backend.sh`:**
- Activates venv, runs `pyinstaller --onedir --name backend app/main.py`
- Outputs to `backend/dist/`

**Verification:** `electron-builder --dir` produces an unpacked app directory.

---

### Phase 4 — CI Pipeline

#### Step 4.1: GitHub Actions Workflow

**Objective:** Automated testing and building for macOS.

**Create `.github/workflows/build.yml`:**
- **Test job** (runs on macos-latest):
  - Checkout
  - Setup Python 3.11, install backend deps, run `pytest`
  - Setup Node.js 20, install frontend deps, run `npm test`
  - Run `ruff check backend/` and `mypy backend/`
  - Run `npm run lint` in frontend
- **Build job** (runs on macos-latest):
  - Depends on test job
  - Build frontend, build backend (PyInstaller), package with electron-builder for macOS
  - Upload `.dmg` artifact

**Verification:** Push to branch, all CI checks pass.

---

## 5) Dependencies and Sequencing

```
Step 1.1 (scaffold) ──────────────────────────────────────┐
    │                                                       │
    ├── Step 1.2 (schemas)                                  │
    │       │                                               │
    │       ├── Step 1.3 (config manager)                   │
    │       ├── Step 1.4 (LLM providers)                    │
    │       ├── Step 1.5 (session store)                    │
    │       └── Step 1.6 (agent framework)                  │
    │               │                                       │
    │               └── Step 1.7 (file search agent)        │
    │                                                       │
    └── Steps 1.3–1.7 ──► Step 1.8 (orchestrator)          │
                               │                            │
                               └── Step 1.9 (API endpoints) │
                                                            │
Step 2.1 (frontend scaffold) ──────────────────────────────┤  ◄── can start in parallel with Phase 1
    │                                                       │
    ├── Step 2.2 (API service layer)                        │
    │       │                                               │
    │       ├── Step 2.3 (useChat hook)                     │
    │       └── Step 2.4 (useSettings hook)                 │
    │               │                                       │
    │               ├── Step 2.5 (chat UI)                  │
    │               └── Step 2.6 (settings panel)           │
    │                                                       │
    └── Phase 2 complete + Phase 1 complete ──► Phase 3     │
                                                   │        │
                                                   └── Phase 4 (CI)
```

**Parallelizable work:**
- Steps 1.3, 1.4, 1.5, 1.6 can all proceed in parallel after 1.2
- Phase 2 (frontend) can start in parallel with Phase 1 (backend) — they share only the schema/contract
- Steps 2.3 and 2.4 are independent of each other
- Steps 2.5 and 2.6 are independent of each other

---

## 6) Risks and Mitigations

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| 1 | Full-disk file search exceeds 60s | High | Poor UX | Default result limit of 100; skip `/System/Volumes/Data` duplicates; run in thread pool; stream partial results in future iteration |
| 2 | Ollama models lack tool-calling support | Medium | Agent delegation fails | Implement fallback: structured system prompt requesting JSON agent invocations; document recommended models (Llama 3.1 8B+) |
| 3 | PyInstaller bundling fails on macOS | Medium | Can't ship | Test PyInstaller builds in CI on macOS early; have `python-build-standalone` as Plan B |
| 4 | WebSocket connection drops during streaming | Medium | Lost response | Implement exponential backoff reconnect in `useChat`; detect incomplete messages and show error |
| 5 | Python child process management edge cases (zombie processes, port leaks) | Medium | App hangs on restart | Implement PID file tracking; force-kill after timeout; clean up port on shutdown |
| 6 | Large conversation context exceeds LLM token limit | Medium | Truncated responses | Track approximate token count per message; implement sliding window truncation of oldest messages |
| 7 | Azure OpenAI API key stored in plaintext JSON | Low | Credential exposure on shared machine | Set file permissions to `0600`; document risk; plan OS keychain integration for Iteration 2 |

---

## 7) Validation Strategy

### Unit Tests
- **Backend:** `pytest` with `pytest-asyncio` for async tests. Mock external dependencies (Ollama client, OpenAI client, filesystem for search). Target: all modules have corresponding test files.
- **Frontend:** Vitest (bundled with Vite) + React Testing Library. Mock `fetch` and `WebSocket`. Target: all hooks and components have test files.

### Static Checks / Lint / Type Checks
- **Backend:** `ruff check backend/` (linting) + `ruff format --check backend/` (formatting) + `mypy backend/` (type checking)
- **Frontend:** `npm run lint` (ESLint with TypeScript rules) + `tsc --noEmit` (type checking)

### Manual Verification
- End-to-end chat flow: send message → receive streamed response
- File search: "find all .txt files in /tmp" → results displayed with name, path, date
- Agent indicator: visible during file search, disappears after completion
- Settings: switch provider from Ollama to Azure OpenAI, verify next message uses new provider
- Error handling: stop Ollama → send message → see "provider unavailable" error
- New Chat: click "New Chat" → history cleared
- Verify CI build passes on macOS

---

## 8) Definition of Done

- [ ] Backend starts with `uvicorn app.main:app` and responds to `/api/health`
- [ ] WebSocket chat endpoint streams token-by-token responses from both Ollama and Azure OpenAI
- [ ] Orchestrator delegates file search requests to FileSearchAgent via LLM tool calling
- [ ] File search returns results with file name, path, last modified date, and size
- [ ] Agent status indicator ("File Search Agent is working…") appears during agent execution and disappears after
- [ ] Multi-turn conversation context is maintained within a session
- [ ] "New Chat" clears context and starts fresh
- [ ] Settings panel allows switching between Ollama and Azure OpenAI with connection details
- [ ] Provider health check shows availability status in settings
- [ ] Invalid provider config shows clear error messages in chat
- [ ] Chat UI renders markdown (bold, lists, code blocks) correctly
- [ ] Streaming responses display incrementally (not as a single block)
- [ ] Electron app launches, spawns Python backend, and loads frontend
- [ ] All backend unit tests pass (`pytest`)
- [ ] All frontend unit tests pass (`npm test`)
- [ ] `ruff check` and `mypy` pass with no errors
- [ ] ESLint and `tsc --noEmit` pass with no errors
- [ ] CI pipeline runs tests and builds on macOS
- [ ] Packaged installer produced: `.dmg`
