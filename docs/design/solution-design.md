# AI Personal Assistant — Solution Design Document

## 1. Problem Framing

A cross-platform desktop AI personal assistant that provides a conversational chat interface backed by user-configurable LLM providers (Ollama local, Azure OpenAI cloud). The system orchestrates specialized agents — starting with a file search agent for MVP — and must be architected for easy agent expansion. Conversation state is ephemeral (session-scoped only in MVP). The UI must match the quality bar of modern AI chat applications (streaming, markdown, responsive layout).

---

## 2. Assumptions and Constraints

| Category | Detail |
|----------|--------|
| **Assumption** | No conversation persistence in MVP; session state is in-memory only |
| **Assumption** | Single agent (file search) for MVP; additional agents in future iterations |
| **Assumption** | File search includes system directories; permission errors are gracefully handled |
| **Assumption** | User has Ollama installed locally or has an Azure OpenAI resource provisioned |
| **Constraint** | Must run on macOS, Windows, and Linux from a single codebase |
| **Constraint** | Chat UI must stream tokens, render markdown, and adapt responsively |
| **Constraint** | All user data remains local; no telemetry unless opt-in |
| **Assumption** | Python backend inferred from existing workspace setup (`backend/.venv`); not mandated by requirements |

---

## 3. Project Stack Inference

The workspace is greenfield with a Python-oriented setup. No frontend code exists yet.

**Inferred/Selected Stack:**

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Desktop shell** | Electron | Proven cross-platform desktop framework; largest ecosystem for desktop web-hybrid apps |
| **Frontend** | React + TypeScript | Component model suits chat UI; rich markdown and streaming libraries available |
| **Backend** | Python (FastAPI) | Async-native, excellent LLM SDK ecosystem (openai, ollama-python), lightweight |
| **IPC** | Local HTTP + WebSocket (FastAPI ↔ Electron renderer) | Clean process boundary; WebSocket for streaming; avoids tight coupling |
| **LLM SDKs** | `openai` (Azure OpenAI), `ollama` (Ollama) | Official/first-party SDKs with streaming support |
| **Packaging** | electron-builder + PyInstaller (bundled Python backend) | Single installer per platform |

---

## 4. Architecture — Electron + Embedded Python Backend

Electron hosts the React frontend. A bundled Python process runs FastAPI on a local port. Communication is via HTTP REST for request/response and WebSocket for streaming. The Python backend owns all LLM interaction, orchestration, and agent execution.

| Attribute | Rating |
|-----------|--------|
| Cross-platform | Excellent — Electron + Python both cross-platform |
| Complexity | Medium — two-process model requires lifecycle management |
| Scalability (agent expansion) | Excellent — agents are Python classes, easy to add |
| UI quality | Excellent — full web tech stack for UI |
| Delivery speed | High — large ecosystem, familiar patterns |

**Why this architecture:** The UI quality requirement ("comparable to Claude/ChatGPT desktop experiences") is the dominant constraint. Electron's Chromium renderer guarantees consistent, high-quality rendering across all three platforms. The Python backend provides the richest LLM SDK ecosystem and aligns with the existing workspace setup. The two-process model cleanly separates concerns and makes the agent framework independently testable.

The bundle size trade-off (~150-200MB) is acceptable for a desktop application of this nature.

---

## 6. C4-Style Component View

### System Context

```
[End User] --(desktop app)--> [AI Personal Assistant]
[AI Personal Assistant] --(HTTP/REST)--> [Ollama (local)]
[AI Personal Assistant] --(HTTPS/REST)--> [Azure OpenAI (cloud)]
[AI Personal Assistant] --(OS filesystem API)--> [Local Filesystem]
```

### Container View

```
┌─────────────────────────────────────────────────────────┐
│                   AI Personal Assistant                   │
│                                                          │
│  ┌──────────────────────┐    ┌────────────────────────┐  │
│  │   Electron Shell      │    │   Python Backend       │  │
│  │                        │    │   (FastAPI process)    │  │
│  │  ┌──────────────────┐ │    │                        │  │
│  │  │  React Frontend   │ │    │  ┌──────────────────┐ │  │
│  │  │  (TypeScript)     │◄├────┤──┤  API Layer       │ │  │
│  │  │                   │ │WS  │  │  (FastAPI)       │ │  │
│  │  │  • Chat UI        │ │HTTP│  └────────┬─────────┘ │  │
│  │  │  • Settings Panel │ │    │           │           │  │
│  │  │  • Agent Status   │ │    │  ┌────────▼─────────┐ │  │
│  │  └──────────────────┘ │    │  │  Orchestrator    │ │  │
│  │                        │    │  │  (Intent+Router) │ │  │
│  │  ┌──────────────────┐ │    │  └────────┬─────────┘ │  │
│  │  │  Main Process     │ │    │           │           │  │
│  │  │  (lifecycle mgmt) │ │    │  ┌────────▼─────────┐ │  │
│  │  └──────────────────┘ │    │  │  Agent Registry  │ │  │
│  └──────────────────────┘    │  │  ┌─────────────┐  │ │  │
│                               │  │  │File Search  │  │ │  │
│                               │  │  │Agent        │  │ │  │
│                               │  │  └─────────────┘  │ │  │
│                               │  └──────────────────┘ │  │
│                               │           │           │  │
│                               │  ┌────────▼─────────┐ │  │
│                               │  │  LLM Provider    │ │  │
│                               │  │  Abstraction     │ │  │
│                               │  │  ┌─────┐┌──────┐ │ │  │
│                               │  │  │Ollama││Azure │ │ │  │
│                               │  │  └─────┘└──────┘ │ │  │
│                               │  └──────────────────┘ │  │
│                               │                        │  │
│                               │  ┌──────────────────┐ │  │
│                               │  │  Config Manager  │ │  │
│                               │  └──────────────────┘ │  │
│                               └────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Component View (Python Backend Detail)

| Component | Responsibility |
|-----------|---------------|
| **API Layer** | FastAPI app exposing REST + WebSocket endpoints; handles request validation, error serialization |
| **Orchestrator** | Manages conversation state, detects intent via LLM function-calling / tool-use, routes to agents, streams results back |
| **Agent Registry** | Maintains registered agents with metadata (name, description, trigger schema); supports dynamic registration |
| **File Search Agent** | Walks filesystem using `os.scandir`/`pathlib`, matches by name/glob, returns structured results |
| **LLM Provider Abstraction** | Strategy pattern; uniform interface for chat completion with streaming; concrete implementations for Ollama and Azure OpenAI |
| **Config Manager** | Reads/writes user settings to a local JSON/TOML file; validates provider configuration |

---

## 7. Interface and Data Contracts

### 7.1 WebSocket — Chat Streaming

**Endpoint:** `ws://localhost:{port}/ws/chat`

**Client → Server (Send Message):**
```json
{
  "type": "user_message",
  "session_id": "uuid-v4",
  "content": "Find all PDF files in my Documents folder"
}
```

**Server → Client (Streaming Events):**
```json
{ "type": "agent_status", "agent_name": "File Search", "status": "working" }
{ "type": "token", "content": "Searching" }
{ "type": "token", "content": " your Documents folder..." }
{ "type": "agent_status", "agent_name": "File Search", "status": "complete" }
{ "type": "agent_result", "data": { "files": [...] } }
{ "type": "token", "content": "I found 3 PDF files..." }
{ "type": "done" }
```

**Server → Client (Error):**
```json
{ "type": "error", "code": "PROVIDER_UNAVAILABLE", "message": "Ollama is not running..." }
```

### 7.2 REST — Settings

**GET /api/settings**
```json
{
  "llm_provider": "ollama",
  "ollama": { "base_url": "http://localhost:11434", "model": "llama3.1" },
  "azure_openai": { "endpoint": "", "api_key": "", "deployment": "", "api_version": "2024-06-01" }
}
```

**PUT /api/settings**
Same schema as GET response body. Returns `200` with updated settings or `422` with validation errors.

**GET /api/settings/providers/status**
```json
{
  "ollama": { "available": true, "models": ["llama3.1", "mistral"] },
  "azure_openai": { "available": true }
}
```

### 7.3 REST — Session Management

**POST /api/sessions** — Creates a new session, returns `{ "session_id": "..." }`

**DELETE /api/sessions/{session_id}** — Clears session context

### 7.4 Agent Interface Contract (Internal Python)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator

@dataclass
class AgentMetadata:
    name: str            # e.g., "File Search"
    description: str     # Used by orchestrator for intent matching
    parameters_schema: dict  # JSON Schema for tool/function calling

@dataclass
class AgentResult:
    success: bool
    data: dict          # Structured result data
    summary: str        # Human-readable summary for the LLM to incorporate

class BaseAgent(ABC):
    @abstractmethod
    def metadata(self) -> AgentMetadata: ...

    @abstractmethod
    async def execute(self, parameters: dict) -> AgentResult: ...
```

### 7.5 LLM Provider Interface Contract (Internal Python)

```python
from abc import ABC, abstractmethod
from typing import AsyncIterator
from dataclasses import dataclass

@dataclass
class ChatMessage:
    role: str       # "system" | "user" | "assistant" | "tool"
    content: str
    tool_calls: list | None = None
    tool_call_id: str | None = None

class BaseLLMProvider(ABC):
    @abstractmethod
    async def chat_completion_stream(
        self,
        messages: list[ChatMessage],
        tools: list[dict] | None = None,
    ) -> AsyncIterator[str]: ...

    @abstractmethod
    async def chat_completion(
        self,
        messages: list[ChatMessage],
        tools: list[dict] | None = None,
    ) -> ChatMessage: ...

    @abstractmethod
    async def health_check(self) -> bool: ...
```

### 7.6 File Search Agent — Result Schema

```json
{
  "files": [
    {
      "name": "report.pdf",
      "path": "/Users/user/Documents/report.pdf",
      "last_modified": "2026-03-15T10:23:00Z",
      "size_bytes": 245760
    }
  ],
  "directories_searched": 1542,
  "directories_skipped": 3,
  "skipped_reasons": ["Permission denied: /private/var/..."]
}
```

---

## 8. Component Design Detail

### 8.1 Chat UI / Frontend

**Technology:** React 18+ with TypeScript, Vite bundler

**Key Libraries:**
- `react-markdown` + `remark-gfm` — Markdown rendering with GitHub-Flavored Markdown
- `react-syntax-highlighter` — Code block highlighting
- CSS Modules or Tailwind CSS — Styling

**Structure:**
```
frontend/
├── src/
│   ├── components/
│   │   ├── ChatWindow.tsx       # Main chat container, message list
│   │   ├── MessageBubble.tsx    # Individual message (user/assistant)
│   │   ├── AgentIndicator.tsx   # "File Search Agent is working…" pill
│   │   ├── InputBar.tsx         # Text input + send button
│   │   ├── SettingsPanel.tsx    # LLM provider configuration
│   │   └── Sidebar.tsx          # New chat button, session list (future)
│   ├── hooks/
│   │   ├── useChat.ts           # WebSocket connection, message state
│   │   └── useSettings.ts       # Settings REST calls
│   ├── services/
│   │   └── api.ts               # HTTP/WS client helpers
│   └── App.tsx
├── index.html
├── package.json
└── vite.config.ts
```

**Streaming UX:** The `useChat` hook maintains a WebSocket connection per session. On each `token` event, the current assistant message is appended to and re-rendered. The `agent_status` events toggle the `AgentIndicator` component visibility. A `done` event finalises the message.

**Responsive layout:** Flexbox-based layout. Chat messages use `max-width: 720px` centred container. Input bar is fixed to bottom. Window minimum size enforced at 400×500px via Electron.

### 8.2 Backend / API Layer

**Technology:** FastAPI 0.110+, Python 3.11+, uvicorn

**Structure:**
```
backend/
├── app/
│   ├── main.py              # FastAPI app, startup/shutdown, CORS
│   ├── api/
│   │   ├── chat.py           # WebSocket endpoint
│   │   ├── settings.py       # Settings REST endpoints
│   │   └── sessions.py       # Session management endpoints
│   ├── core/
│   │   ├── config.py         # Config manager (load/save settings)
│   │   ├── orchestrator.py   # Orchestrator logic
│   │   └── session.py        # In-memory session store
│   ├── agents/
│   │   ├── base.py           # BaseAgent ABC
│   │   ├── registry.py       # AgentRegistry
│   │   └── file_search.py    # FileSearchAgent
│   ├── llm/
│   │   ├── base.py           # BaseLLMProvider ABC
│   │   ├── ollama.py         # OllamaProvider
│   │   └── azure_openai.py   # AzureOpenAIProvider
│   └── models/
│       └── schemas.py        # Pydantic models for API
├── tests/
├── pyproject.toml
└── requirements.txt
```

**Startup:** FastAPI `lifespan` context manager initialises the agent registry, loads config, and pre-warms the LLM provider health check.

**CORS:** Configured to allow only `http://localhost:*` origins (Electron renderer).

### 8.3 Orchestrator

The orchestrator is the central coordination point. It uses LLM **tool/function calling** to decide when to delegate to an agent.

**Flow:**

1. User message arrives via WebSocket.
2. Orchestrator prepends conversation history (from in-memory session store).
3. Orchestrator constructs the LLM request with registered agent metadata exposed as **tools** (function definitions).
4. LLM responds with either:
   - **Direct text** → stream tokens to client.
   - **Tool call** → emit `agent_status` event, execute the agent, feed the result back to the LLM as a tool response, then stream the LLM's synthesis of the result.
5. Final response is appended to session history.

**Intent Detection Strategy:** Rather than building a custom intent classifier, we leverage the LLM's native function/tool-calling capability. Each registered agent exposes its metadata as an OpenAI-compatible tool definition. The LLM decides whether to call a tool based on the user's message. This approach:
- Requires no training data or custom models
- Automatically benefits from LLM improvements
- Works identically across Ollama (models supporting tool calling like Llama 3.1+) and Azure OpenAI

**Fallback:** If the active LLM model does not support tool calling (some smaller Ollama models), the orchestrator falls back to a keyword/prompt-based detection with a structured system prompt that requests JSON-formatted agent invocations.

### 8.4 Agent Framework

**AgentRegistry:**
```python
class AgentRegistry:
    def __init__(self):
        self._agents: dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        meta = agent.metadata()
        self._agents[meta.name] = agent

    def get(self, name: str) -> BaseAgent | None:
        return self._agents.get(name)

    def all_metadata(self) -> list[AgentMetadata]:
        return [a.metadata() for a in self._agents.values()]

    def as_tools(self) -> list[dict]:
        """Convert all agent metadata to OpenAI function-calling tool definitions."""
        return [
            {
                "type": "function",
                "function": {
                    "name": meta.name.lower().replace(" ", "_"),
                    "description": meta.description,
                    "parameters": meta.parameters_schema,
                }
            }
            for meta in self.all_metadata()
        ]
```

**Adding a new agent (future):** Implement `BaseAgent`, call `registry.register(MyNewAgent())` in the startup sequence. No orchestrator changes needed — the agent's tool definition is automatically included in LLM calls.

### 8.5 File Search Agent

**Implementation approach:**

- Uses `os.scandir()` with recursive traversal for performance (faster than `os.walk` or `glob` for deep trees).
- Supports glob patterns (`*.pdf`) and substring matching on file names.
- Accepts an optional `directory` parameter; defaults to filesystem root (`/` on Unix, all drive letters on Windows).
- Runs in a thread pool executor (`asyncio.to_thread`) to avoid blocking the event loop.
- Gracefully catches `PermissionError` and `OSError`, logging skipped directories.
- Implements a configurable result limit (default 100) to prevent overwhelming the UI and LLM context.

**Parameters schema:**
```json
{
  "type": "object",
  "properties": {
    "pattern": {
      "type": "string",
      "description": "File name or glob pattern to search for, e.g. '*.pdf' or 'report'"
    },
    "directory": {
      "type": "string",
      "description": "Directory to search in. If omitted, searches all directories."
    }
  },
  "required": ["pattern"]
}
```

**Platform-specific considerations:**
- **Windows:** Enumerate drive letters via `string.ascii_uppercase` + `os.path.exists`; handle long paths (`\\?\` prefix or enable long path support).
- **macOS:** Skip `/System/Volumes/Data` duplicates if they mirror user-space paths.
- **Linux:** Skip pseudo-filesystems (`/proc`, `/sys`, `/dev`) by default but include `/` and all real mount points.

### 8.6 LLM Provider Abstraction

**Strategy pattern** with two concrete implementations:

**OllamaProvider:**
- Uses the `ollama` Python package (async client).
- Connects to `http://localhost:11434` by default (configurable).
- Streams via `ollama.AsyncClient.chat(stream=True)`.
- Health check: `GET /api/tags` endpoint.
- Tool calling: Supported in Ollama for compatible models (Llama 3.1+, Mistral, etc.).

**AzureOpenAIProvider:**
- Uses the `openai` Python package with `AzureOpenAI` client.
- Requires: endpoint, API key, deployment name, API version.
- Streams via `client.chat.completions.create(stream=True)`.
- Health check: lightweight completion request or model list call.
- Tool calling: Fully supported.

**Provider factory:**
```python
def create_provider(config: Settings) -> BaseLLMProvider:
    match config.llm_provider:
        case "ollama":
            return OllamaProvider(config.ollama)
        case "azure_openai":
            return AzureOpenAIProvider(config.azure_openai)
```

**Mid-session switching:** When the user changes provider via settings, the backend re-creates the provider instance. The session's conversation history (list of `ChatMessage`) is preserved and passed to the new provider on the next request.

### 8.7 Settings / Configuration Management

**Storage:** Local JSON file at:
- **macOS:** `~/Library/Application Support/ai-personal-assistant/settings.json`
- **Windows:** `%APPDATA%/ai-personal-assistant/settings.json`
- **Linux:** `~/.config/ai-personal-assistant/settings.json`

Resolved via `platformdirs` Python package.

**Schema validation:** Pydantic model for settings; invalid values rejected at the API layer with clear error messages.

**Credential security:** Azure OpenAI API key is stored in the local config file with restrictive file permissions (`0600`). This is acceptable for MVP (single-user desktop app). Future improvement: integrate with OS keychain (macOS Keychain, Windows Credential Manager, libsecret on Linux).

---

## 9. Communication & Data Flow

### 9.1 Startup Sequence

```
1. User launches app → Electron main process starts
2. Electron main process spawns Python backend as child process
   - Finds available port (or uses fixed port with fallback)
   - Passes port via command-line arg or env var
3. Python backend starts FastAPI/uvicorn on the designated port
4. Electron main process polls backend health endpoint (/api/health)
5. Once healthy, Electron loads React frontend in BrowserWindow
6. Frontend connects WebSocket to backend
```

### 9.2 Chat Message Flow

```
User types message
        │
        ▼
React InputBar ──POST──► useChat hook
        │
        ▼
WebSocket send { type: "user_message", content: "..." }
        │
        ▼
FastAPI WebSocket endpoint (chat.py)
        │
        ▼
Orchestrator.handle_message(session_id, content)
        │
        ├──► Prepend session history
        ├──► Build messages array with system prompt
        ├──► Call LLM with tools=[agent definitions]
        │
        ├─── LLM returns text ──► stream tokens via WebSocket
        │
        └─── LLM returns tool_call ──►
                ├──► Send agent_status "working" via WebSocket
                ├──► AgentRegistry.get(tool_name).execute(params)
                ├──► Send agent_status "complete" via WebSocket
                ├──► Feed agent result back to LLM as tool response
                └──► Stream LLM's synthesized response via WebSocket
        │
        ▼
Append assistant response to session history
Send { type: "done" }
```

### 9.3 IPC Mechanism

- **Protocol:** HTTP/1.1 (REST) + WebSocket, both over localhost TCP.
- **Port:** Dynamically selected at startup; electron main process communicates port to renderer via IPC.
- **Security:** Requests validated with a shared secret token (generated per-launch, passed to both processes). This prevents other local processes from calling the API.
- **Lifecycle:** Electron main process monitors the Python child process; restarts it if it crashes; gracefully terminates on app quit via `SIGTERM`/`SIGINT`.

---

## 10. Cross-Platform Strategy

### 10.1 Electron + Python Bundling

| Concern | Approach |
|---------|----------|
| **Python distribution** | Bundle a standalone Python runtime using PyInstaller (`--onedir` mode) or use `python-build-standalone` (pre-built, relocatable Python). Avoids requiring user to install Python. |
| **Platform builds** | electron-builder configured for: `.dmg` (macOS), `.exe`/NSIS installer (Windows), `.AppImage` + `.deb` (Linux) |
| **Architecture** | Build for x64 and arm64 (macOS Apple Silicon, Linux ARM) |
| **Code signing** | macOS: notarization via `electron-notarize`; Windows: Authenticode signing |

### 10.2 Platform-Specific Concerns

| Platform | Concern | Mitigation |
|----------|---------|------------|
| **macOS** | App Sandbox / Gatekeeper may restrict filesystem access | Ship outside App Store; full disk access entitlement if needed |
| **macOS** | Apple Silicon vs Intel | Universal binary or separate arm64/x64 builds |
| **Windows** | Long file paths (>260 chars) | Use `\\?\` prefix in file search; document Windows long path registry setting |
| **Windows** | Firewall prompts for localhost server | Use `127.0.0.1` explicitly; avoid `0.0.0.0` binding |
| **Linux** | Various display servers (X11/Wayland) | Electron handles this; test on both |
| **Linux** | File permissions vary by distro | Graceful PermissionError handling in file search agent |

### 10.3 Project Layout

```
ai-personal-assistant/
├── docs/
│   ├── requirements/
│   │   └── business-requirements.md
│   └── design/
│       └── solution-design.md
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── core/
│   │   ├── agents/
│   │   ├── llm/
│   │   └── models/
│   ├── tests/
│   ├── pyproject.toml
│   └── requirements.txt
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── electron/
│   ├── main.ts              # Electron main process
│   ├── preload.ts           # Preload script (IPC bridge)
│   └── python-manager.ts    # Python backend lifecycle management
├── scripts/
│   ├── build-backend.sh     # PyInstaller build script
│   └── package.sh           # Full app packaging
├── .github/
│   └── workflows/
│       └── build.yml         # CI: test + build per platform
├── package.json              # Root: Electron + build scripts
└── electron-builder.yml      # Packaging config
```

---

## 11. Non-Functional Requirements

### 11.1 Performance

| Metric | Target | Mechanism |
|--------|--------|-----------|
| Time to first token | < 2s (Ollama), < 3s (Azure OpenAI) | Streaming from first token; pre-warmed connections |
| File search (typical query) | < 10s for indexed directory, < 60s for full disk | Async directory traversal; early result streaming; result cap at 100 |
| App startup to ready | < 5s | Backend health poll with 100ms interval; preload frontend while backend starts |
| Memory usage (idle) | < 300MB | Electron ~150MB + Python ~50-100MB baseline |

### 11.2 Security

| Concern | Mitigation |
|---------|------------|
| Local API exposure | Bind to `127.0.0.1` only; per-session shared secret token in request headers |
| Azure OpenAI credentials | Stored in local config with `0600` permissions; never sent to frontend; future: OS keychain |
| File search results sent to cloud LLM | Only file metadata (name, path) sent as context, not file contents; document this clearly to user |
| Electron security | `nodeIntegration: false`, `contextIsolation: true`, CSP headers; no `shell.openExternal` without validation |
| Dependency supply chain | Pin dependency versions; use `pip audit` and `npm audit` in CI |

### 11.3 Reliability

- Backend crash recovery: Electron monitors child process and restarts automatically.
- WebSocket reconnection: Frontend implements exponential backoff reconnect.
- LLM provider failures: Clear error messages; no silent failures; user can switch providers.

### 11.4 Maintainability

- Clear separation between frontend, backend, and Electron shell.
- Backend is independently runnable (`uvicorn app.main:app`) for development/testing without Electron.
- Agent framework uses standard ABCs; adding agents requires no orchestrator changes.
- Type annotations throughout Python backend; TypeScript in frontend.

---

## 12. Key Decisions (ADR Style)

### ADR-001: Electron for Desktop Shell

- **Context:** Need cross-platform desktop app with modern chat UI comparable to ChatGPT/Claude.
- **Options:** Electron, Tauri, Qt
- **Decision:** Electron
- **Rationale:** Guaranteed rendering consistency via Chromium; largest ecosystem for desktop hybrid apps; proven by similar products (VS Code, Slack, Discord). Bundle size trade-off is acceptable.
- **Consequences:** ~150MB base overhead; must manage Chromium updates and security patches.

### ADR-002: Python FastAPI for Backend

- **Context:** Backend needs async streaming, LLM SDK access, cross-platform filesystem operations.
- **Options:** Python/FastAPI, Node.js/Express
- **Decision:** Python with FastAPI
- **Rationale:** Best LLM SDK ecosystem (openai, ollama); async-native with uvicorn; aligns with workspace setup; rich filesystem libraries.
- **Consequences:** Need to bundle Python runtime (~40MB); two-language project (TypeScript frontend + Python backend).

### ADR-003: WebSocket for Chat Streaming

- **Context:** Chat responses must stream token-by-token to the UI.
- **Options:** WebSocket, Server-Sent Events (SSE), HTTP long-polling
- **Decision:** WebSocket
- **Rationale:** Bidirectional communication needed (user can send messages while assistant is responding); native FastAPI WebSocket support; lower latency than SSE for bidirectional flows.
- **Consequences:** Slightly more complex connection management than SSE; need reconnection logic.

### ADR-004: LLM Tool Calling for Intent Detection

- **Context:** Orchestrator needs to determine when to delegate to a specialized agent.
- **Options:** Custom intent classifier, keyword matching, LLM tool/function calling
- **Decision:** LLM native tool/function calling
- **Rationale:** No training data needed; scales automatically with new agents (just register new tool definitions); works with both Azure OpenAI and Ollama (Llama 3.1+); most natural integration.
- **Consequences:** Requires LLM models that support tool calling; need fallback for models that don't.

### ADR-005: Local HTTP for IPC (Electron ↔ Python)

- **Context:** Frontend (Electron renderer) needs to communicate with Python backend.
- **Options:** Electron IPC + Node.js bridge, stdio pipes, local HTTP/WebSocket, Unix domain socket
- **Decision:** Local HTTP + WebSocket on `127.0.0.1`
- **Rationale:** Clean process boundary; backend is independently testable; standard protocols; no custom serialisation; works identically across platforms.
- **Consequences:** Must manage port allocation and per-session auth token; slight overhead vs. stdio (negligible for this use case).

### ADR-006: In-Memory Session Store for MVP

- **Context:** Conversation history needed within a session but not across sessions.
- **Options:** In-memory dict, SQLite, Redis
- **Decision:** In-memory Python dict keyed by session ID.
- **Rationale:** Simplest possible approach for ephemeral sessions; no persistence requirement in MVP; trivially replaced with SQLite in Iteration 2.
- **Consequences:** All context lost on backend restart/crash; acceptable per requirements.

---

## 13. Risks and Mitigations

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| 1 | Full-disk file search is slow (>60s) | High | Poor UX | Stream partial results as found; default result limit of 100; skip pseudo-filesystems; show progress count ("X files found so far…") |
| 2 | Permission errors during file search | High | Incomplete results | Catch `PermissionError` per-directory; report skipped count in results; don't halt on individual errors |
| 3 | Ollama model doesn't support tool calling | Medium | Agent delegation fails | Implement fallback prompt-based detection; document recommended models (Llama 3.1 8B+) |
| 4 | Python bundling complexity varies by platform | Medium | Build failures | Test PyInstaller builds in CI on all three platforms; consider `python-build-standalone` as alternative |
| 5 | Electron security vulnerabilities | Low | Security exposure | Keep Electron updated; enforce CSP; disable `nodeIntegration`; use `contextIsolation` |
| 6 | Large conversation context exceeds LLM token limit | Medium | Truncated/failed responses | Implement sliding window or summarisation of older messages; track token count |
| 7 | Port conflict on localhost | Low | App fails to start | Dynamic port selection with retry; store selected port for frontend discovery |

---

## 14. Delivery Roadmap

### Phase 1 — Foundation (Weeks 1-3)

**Goal:** Backend scaffold + basic chat working end-to-end.

- [ ] Python backend project setup (FastAPI, project structure, pyproject.toml)
- [ ] LLM provider abstraction + Ollama implementation
- [ ] LLM provider abstraction + Azure OpenAI implementation
- [ ] Basic orchestrator (no agents, direct LLM pass-through)
- [ ] WebSocket streaming endpoint
- [ ] React frontend scaffold (Vite + TypeScript)
- [ ] Chat UI components (message list, input bar, markdown rendering)
- [ ] WebSocket client hook
- [ ] Electron shell with Python backend lifecycle management

**Milestone:** User can chat with LLM through the desktop app with streaming responses.

### Phase 2 — Agent Framework + File Search (Weeks 4-5)

- [ ] Agent base class and registry
- [ ] Orchestrator tool-calling integration
- [ ] File search agent implementation
- [ ] Agent status indicator in UI
- [ ] Cross-platform file search testing (macOS, Windows, Linux)

**Milestone:** User can ask to find files; orchestrator delegates to file search agent with status visibility.

### Phase 3 — Settings + Polish (Week 6)

- [ ] Settings REST API + config persistence
- [ ] Settings UI panel (provider selection, connection details)
- [ ] Provider health check and error messaging
- [ ] Session management (new chat, context clearing)
- [ ] UI polish (responsive layout, error states, loading states)

**Milestone:** Feature-complete MVP.

### Phase 4 — Packaging + Release (Week 7)

- [ ] PyInstaller backend bundling per platform
- [ ] electron-builder packaging (dmg, exe, AppImage)
- [ ] CI pipeline for automated builds
- [ ] Manual QA on all three platforms
- [ ] Documentation (README, quickstart, recommended Ollama models)

**Milestone:** Distributable installers for macOS, Windows, and Linux.

### Decision Checkpoints

| When | Decision |
|------|----------|
| End of Phase 1 | Validate streaming performance meets targets; confirm Electron + Python lifecycle is stable |
| End of Phase 2 | Evaluate file search performance on full disk; decide if indexing is needed pre-Iteration 2 |
| End of Phase 3 | Stakeholder review of UX quality bar; decide if additional polish sprint needed |
| Pre-release | Security review (credential storage, API exposure, Electron config) |

---

## 15. Future Extensibility

### Iteration 2 — Conversation Persistence

- Replace in-memory session store with SQLite (via `aiosqlite`).
- Add session list UI in sidebar.
- Add session resume on app reopen.
- No architectural changes needed — swap the session store implementation behind the existing interface.

### Future Agents

The agent framework is designed for zero-orchestrator-change expansion:

1. Create a new class implementing `BaseAgent`.
2. Define `metadata()` with name, description, and parameters JSON schema.
3. Implement `execute()` with the agent's logic.
4. Register in startup: `registry.register(MyNewAgent())`.

The orchestrator automatically includes the new agent's tool definition in LLM calls. No routing rules, no intent training data.

**Candidate future agents:**
- **Terminal Agent** — Execute shell commands requested by user.
- **Calendar Agent** — Query/create calendar events via OS calendar APIs.
- **Email Agent** — Draft/search emails via IMAP/SMTP or OS mail APIs.
- **File Content Search Agent** — Full-text search within files (may require indexing infrastructure).
- **Web Search Agent** — Search the web via API (Bing, Google).

### Additional LLM Providers

Adding a new provider requires:
1. Implement `BaseLLMProvider` (e.g., for Anthropic, Google Gemini, local llama.cpp).
2. Add provider config schema to settings model.
3. Add case to provider factory.
4. Add UI fields in settings panel.

### Plugin System (Long-term)

If the agent count grows significantly, consider a plugin system:
- Agents as installable Python packages with entry points.
- Auto-discovery via `importlib.metadata.entry_points()`.
- Hot-reload without app restart.

This is not needed for MVP or near-term iterations but the current `BaseAgent` + `AgentRegistry` design is compatible with this evolution.
