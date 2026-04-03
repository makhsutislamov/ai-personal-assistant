# AI Personal Assistant - Implementation Plan

Date: 2026-04-03
Source requirements: [docs/requirements/business-requirements.md](requirements/business-requirements.md)
Source architecture: [docs/architecture/solution-architecture.md](architecture/solution-architecture.md)

---

## 1) Goal and Scope

### Implementation Target
Build a desktop-first AI Personal Assistant with:
- Multi-turn conversational interface with structured note generation.
- Memory/knowledge base with semantic search across conversations, Apple Notes, and browser captures.
- Configurable memory write modes (auto, ask, manual).
- Sensitivity-aware model routing (Azure OpenAI for non-sensitive, Ollama for sensitive/local).
- Agentic task creation, tracking, and completion with confirmation gates.
- Privacy controls: consent management, deletion, immutable audit trail.
- KPI instrumentation for recall accuracy and task completion rate.

### In Scope (MVP / Phase 1)
- Electron desktop shell with React UI.
- Python FastAPI backend running as local sidecar process.
- SQLite + SQLCipher for operational data.
- SQLite vector extension for semantic search.
- Ollama and Azure OpenAI model integration with policy-guarded routing.
- Apple Notes connector (read/sync).
- Browser capture via Manifest V3 Chrome extension.
- Audit logging with hash-chained events.
- Local OpenTelemetry instrumentation.

### Out of Scope
- Screenshot capture workflows.
- Generic active app integrations beyond Apple Notes and Browser.
- Enterprise multi-tenant features.
- Cloud telemetry or cloud-hosted services.

---

## 2) Repository Findings

### Current State
- Greenfield repository: no source code, no package configs, no dependencies.
- Contains only documentation artifacts:
  - `docs/requirements/business-requirements.md` — 45 functional requirements, 16 NFRs, 10 user stories, 20 acceptance criteria.
  - `docs/architecture/solution-architecture.md` — C4 views, module design, API contracts, ADRs, tech stack.
- Contains agent definitions (`.github/agents/`) and prompt templates (`.github/prompts/`).

### Patterns and Conventions
- No existing code patterns to follow; conventions will be established by this plan.
- Architecture specifies: Python FastAPI backend, Electron + React frontend, SQLite + SQLCipher storage, local-first observability.
- API contract style: RESTful `/v1/` prefix, Pydantic request/response models.
- Event-driven internal bus for cross-module communication.

### Constraints from Architecture
- ADR-001: Desktop-first hybrid, local-first observability.
- ADR-002: Policy Guard as hard pre-routing gate.
- ADR-009: Encrypt operational DB via OS keychain-backed keys.
- ADR-010: Stable domain APIs with swappable providers.

---

## 3) Assumptions and Clarifications

### Assumptions
1. Python 3.12+ is available on the development machine.
2. Node.js 20 LTS is available for Electron/React tooling.
3. Ollama is installed and running locally for development.
4. Azure OpenAI endpoint and API key are available for non-sensitive routing testing.
5. macOS is the primary development and deployment target for Phase 1.
6. Apple Notes access will use AppleScript/osascript bridge (macOS native).
7. Browser extension targets Chrome (Chromium) first.
8. Sensitive taxonomy at launch: credentials-only (passwords, tokens, secrets, private keys, connection strings).
9. Memory mode default: `ask`.
10. Work/personal separation: tags/filters only for MVP (no strict profile isolation).

### Clarifications Needed (non-blocking, can proceed with defaults)
1. Grounding strictness: plan assumes allow-with-warning for MVP.
2. Retention defaults: plan assumes 90 days for conversations, unlimited for notes/captures until user deletes.
3. Task completion definition: plan assumes user-confirmed completion or explicit cancel.

---

## 4) Implementation Plan

### Phase 1.0: Project Scaffolding and Infrastructure

#### Step 1.0.1: Initialize Python Backend Project

**Objective:** Create the FastAPI backend project with standard tooling.

**Changes:**
- Create `backend/` directory at project root.
- Create `backend/pyproject.toml` with project metadata and dependencies:
  ```
  dependencies:
    fastapi >= 0.135.3
    uvicorn[standard] >= 0.42.0
    pydantic >= 2.12.5
    pydantic-settings >= 2.13.1
    sqlalchemy >= 2.0.48
    aiosqlite >= 0.22.1
    sqlcipher3 >= 0.6.2
    sqlite-vec >= 0.1.9
    openai >= 2.30.0
    ollama >= 0.6.1
    opentelemetry-api >= 1.40.0
    opentelemetry-sdk >= 1.40.0
    httpx >= 0.28.1
    structlog >= 25.5.0
  dev-dependencies:
    pytest >= 9.0.2
    pytest-asyncio >= 1.3.0
    pytest-cov >= 7.1.0
    ruff >= 0.15.9
    mypy >= 1.20.0
  ```
- Create `backend/src/assistant/` Python package with `__init__.py`.
- Create `backend/src/assistant/main.py` — FastAPI application factory.
- Create `backend/src/assistant/config.py` — Pydantic Settings model for all configuration knobs:
  - `memory_mode`: `auto | ask | manual` (default: `ask`)
  - `routing_preference`: `azure_openai | ollama` (default: `azure_openai`)
  - `sensitive_local_only`: `bool` (default: `True`)
  - `ollama_base_url`: `str` (default: `http://localhost:11434`)
  - `azure_openai_endpoint`: `str`
  - `azure_openai_api_key`: `str` (loaded from keychain at runtime)
  - `azure_openai_deployment`: `str`
  - `azure_openai_api_version`: `str` (default: `2024-02-01`)
  - `db_path`: `str`
  - `db_encryption_key`: `str` (loaded from keychain at runtime)
- Create `backend/tests/` directory with `conftest.py`, `__init__.py`.

**Execution:**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

**Unit tests:**
- `tests/test_config.py`: Validate config loading with defaults, env overrides, and missing required fields.

**Verification:**
- `ruff check src/` passes.
- `mypy src/` passes.
- `pytest tests/` passes.
- `uvicorn assistant.main:create_app --factory` starts and responds to `GET /health`.

---

#### Step 1.0.2: Initialize Electron Desktop Shell

**Objective:** Create the Electron + React desktop app that launches and manages the Python backend sidecar.

**Changes:**
- Create `desktop/` directory at project root.
- Initialize with `npm init` and install:
  ```
  electron, electron-builder (dev)
  react, react-dom
  typescript, @types/react, @types/react-dom
  vite, @vitejs/plugin-react (dev)
  ```
- Create `desktop/src/main/` — Electron main process:
  - `main.ts`: App lifecycle, window creation, sidecar process management.
  - `preload.ts`: contextBridge exposing `electronAPI` with specific IPC channels only.
  - `sidecar.ts`: Spawn/manage Python FastAPI process, health check polling, graceful shutdown.
- Create `desktop/src/renderer/` — React app:
  - `App.tsx`: Root component with router.
  - `pages/Chat.tsx`: Placeholder chat interface.
  - `pages/Settings.tsx`: Placeholder settings panel.
  - `api/client.ts`: Typed HTTP client wrapping `fetch` to `http://localhost:{port}/v1/...`.
- Create `desktop/electron-builder.yml` for macOS packaging config.

**Execution:**
```bash
cd desktop
npm install
npm run dev  # Starts Electron with hot-reload
```

**Unit tests:**
- `desktop/src/__tests__/api/client.test.ts`: Mock fetch, verify correct URL construction and error handling.

**Verification:**
- Electron window opens and shows React placeholder UI.
- Python sidecar starts and `/health` is reachable.
- `contextIsolation: true` in BrowserWindow webPreferences.
- Preload only exposes explicitly defined IPC methods.

---

#### Step 1.0.3: Database Layer Setup

**Objective:** Create SQLite + SQLCipher database with schema migrations and SQLite vector extension.

**Changes:**
- Create `backend/src/assistant/db/` package:
  - `engine.py`: SQLAlchemy async engine factory with SQLCipher PRAGMA key.
  - `models.py`: SQLAlchemy ORM models for all core entities:
    - `MemoryRecord` (memoryId, sourceType, sourceRef, canonicalText, sensitivityClass, confidence, embedding BLOB, createdAt, updatedAt, deletedAt)
    - `SourceDocument` (sourceId, externalRef, title, syncVersion, syncStatus, consentSnapshot)
    - `BrowserCapture` (captureId, url, title, selectedText, fullPageContentRef, captureMode, createdAt)
    - `TaskRecord` (taskId, objective, owner, dueAt, status, blockedReason, completionOutcome)
    - `ConversationSession` (sessionId, startedAt, endedAt, topicTags)
    - `ConversationMessage` (messageId, sessionId, role, content, createdAt)
    - `NoteItem` (noteId, source, content, tags, sensitivityLevel, createdAt, updatedAt)
    - `RoutingEvent` (eventId, requestId, sensitivityDecision, chosenModel, blockReason, latencyMs, createdAt)
    - `AuditEvent` (eventId, actor, actionType, targetType, targetId, beforeHash, afterHash, createdAt)
    - `UserSettings` (key, value, updatedAt, updatedBy)
  - `migrations.py`: Schema creation and migration logic (run on startup).
  - `vector.py`: SQLite vector extension loading and helper functions for embedding insert/search.
- Create indexes as specified in architecture:
  - `MemoryRecord`: composite on (sourceType, updatedAt), partial on (deletedAt IS NULL).
  - `TaskRecord`: on (status, dueAt).
  - `RoutingEvent`: on (createdAt, sensitivityDecision).

**Unit tests:**
- `tests/db/test_models.py`: Create in-memory SQLite DB, insert/query each entity, verify constraints.
- `tests/db/test_vector.py`: Insert embeddings, run similarity search, verify ordering.
- `tests/db/test_migrations.py`: Run migrations on empty DB, verify all tables exist.

**Verification:**
- All tables created with correct columns and indexes.
- Vector search returns correct nearest neighbors for test embeddings.
- SQLCipher encryption: opening DB without key fails.

---

### Phase 1.1: Core Conversation and Memory

#### Step 1.1.1: Conversation Orchestrator

**Objective:** Implement multi-turn conversation with session management and grounded response generation. Covers FR-01, FR-14, FR-15, FR-16.

**Changes:**
- Create `backend/src/assistant/conversation/` package:
  - `orchestrator.py`:
    - `async def respond(session_id, user_message, settings) -> ChatResponse`
    - Assembles prompt from session history + retrieved context.
    - Calls Policy Guard before model invocation.
    - Calls Model Router to get completion.
    - Returns response with `sources: list[SourceAttribution]` and `model_path: str`.
  - `schemas.py`: Pydantic models:
    - `ChatRequest(session_id: str | None, message: str)`
    - `ChatResponse(response: str, sources: list[SourceAttribution], session_id: str, model_used: str, grounded: bool)`
    - `SourceAttribution(memory_id: str, source_type: str, title: str, snippet: str, created_at: datetime)`
  - `session.py`: Session CRUD — create, get history, append message.
  - `prompt_builder.py`: Assemble system prompt + retrieved context + conversation history into model input. Include grounding instruction and confidence-gate prompt.
- Create `backend/src/assistant/api/chat.py`:
  - `POST /v1/chat/respond` — accepts `ChatRequest`, returns `ChatResponse`.
  - `GET /v1/chat/sessions/{session_id}` — returns session transcript.
- Register router in `main.py`.

**Unit tests:**
- `tests/conversation/test_orchestrator.py`: Mock retrieval and model router; verify grounded response includes sources, ungrounded response triggers clarification.
- `tests/conversation/test_session.py`: Create session, append messages, retrieve history.
- `tests/conversation/test_prompt_builder.py`: Verify prompt structure with/without context.
- `tests/api/test_chat.py`: FastAPI TestClient tests for both endpoints.

**Verification:**
- Chat endpoint returns grounded answer when relevant memory exists.
- Chat endpoint returns uncertainty message when no relevant memory.
- Session history is persisted across requests.

---

#### Step 1.1.2: Memory Service

**Objective:** Implement memory ingestion, candidate flow, deduplication, and deletion. Covers FR-06 through FR-12, FR-37.

**Changes:**
- Create `backend/src/assistant/memory/` package:
  - `service.py`:
    - `async def create_candidate(content, source_type, metadata, sensitivity_class) -> MemoryCandidate`
    - `async def confirm_candidate(candidate_id) -> MemoryRecord`
    - `async def reject_candidate(candidate_id) -> None`
    - `async def auto_ingest(content, source_type, metadata) -> MemoryRecord` (for auto mode)
    - `async def delete_memories(filter: DeleteFilter) -> DeleteResult`
    - `async def detect_duplicate(content, embedding) -> DuplicateResult`
  - `schemas.py`: Pydantic models for candidates, records, delete filters, duplicate results.
  - `embeddings.py`:
    - `async def generate_embedding(text: str) -> list[float]` — calls Ollama embeddings endpoint (local, no sensitive data concern for embeddings).
  - `dedup.py`:
    - Exact hash check + cosine similarity threshold (0.95 default) for near-duplicate detection.
- Create `backend/src/assistant/api/memory.py`:
  - `POST /v1/memory/candidates` — create candidate (ask/manual flow).
  - `POST /v1/memory/confirm` — confirm candidate write.
  - `POST /v1/memory/reject` — reject candidate.
  - `DELETE /v1/memory` — delete by item/source/time range.
- Memory mode logic:
  - `auto`: `auto_ingest` called directly, audit event emitted.
  - `ask`: `create_candidate` called, user sees pending item, confirms or rejects.
  - `manual`: nothing written unless user explicitly triggers save command.
- Register router in `main.py`.

**Unit tests:**
- `tests/memory/test_service.py`: Test candidate lifecycle (create, confirm, reject), auto mode, deletion by each filter type.
- `tests/memory/test_embeddings.py`: Mock Ollama, verify embedding shape and caching.
- `tests/memory/test_dedup.py`: Test exact match, near-duplicate, and non-duplicate scenarios.
- `tests/api/test_memory.py`: FastAPI TestClient tests for all endpoints.

**Verification:**
- Memory candidate flow works for ask mode end-to-end.
- Auto mode writes immediately with audit trail.
- Manual mode produces no writes without explicit action.
- Deletion removes records from DB and vector index.
- Near-duplicate detection flags similar content.

---

#### Step 1.1.3: Retrieval Service

**Objective:** Implement semantic search with source attribution and confidence scoring. Covers FR-13 through FR-18.

**Changes:**
- Create `backend/src/assistant/retrieval/` package:
  - `service.py`:
    - `async def query(text: str, filters: RetrievalFilter | None) -> RetrievalResult`
    - Two-stage: vector search → optional lexical fallback → rerank by recency + confidence.
    - Returns ranked evidence bundle with source attributions.
  - `schemas.py`: `RetrievalFilter(source_types, time_from, time_to)`, `RetrievalResult(items, query_latency_ms)`, `RetrievalItem(memory_id, score, snippet, source)`.
  - `reranker.py`: Score combination: vector similarity * 0.7 + recency_decay * 0.2 + source_priority * 0.1.
- Create `backend/src/assistant/api/retrieval.py`:
  - `POST /v1/retrieval/query` — accepts query text and optional filters.
- Register router in `main.py`.

**Unit tests:**
- `tests/retrieval/test_service.py`: Seed test memories with known embeddings, verify correct ranking.
- `tests/retrieval/test_reranker.py`: Test score combination with various inputs.
- `tests/api/test_retrieval.py`: TestClient for retrieval endpoint.

**Verification:**
- Returns relevant results ranked by combined score.
- Filters by source type and time range work correctly.
- Empty results return gracefully with empty list.
- Latency is tracked and returned in response.

---

### Phase 1.2: Model Routing and Privacy

#### Step 1.2.1: Policy Guard

**Objective:** Implement sensitivity detection and consent enforcement as a hard gate before any model invocation. Covers FR-31, FR-32, FR-36, FR-39.

**Changes:**
- Create `backend/src/assistant/policy/` package:
  - `guard.py`:
    - `async def evaluate(content: str, context: PolicyContext) -> PolicyDecision`
    - Returns `PolicyDecision(allowed_remote: bool, sensitivity_class: str, reason: str, blocked_patterns: list[str])`.
  - `detector.py`:
    - Regex-based patterns for: API keys, tokens, passwords, private keys, connection strings.
    - Pattern list in `backend/src/assistant/policy/patterns.py` — one pattern per line, testable independently.
    - `def detect_sensitive(text: str) -> list[SensitiveMatch]`
  - `consent.py`:
    - `async def check_source_consent(source_type: str) -> bool` — reads consent status from DB.

**Unit tests:**
- `tests/policy/test_detector.py`: Test each pattern against positive and negative samples:
  - API key: `sk-abc123...`, `AKIA...`
  - Passwords: `password=xxx`, `passwd: xxx`
  - Private keys: `-----BEGIN RSA PRIVATE KEY-----`
  - Connection strings: `Server=...;Password=...`
  - Negative: normal text, code snippets without secrets.
- `tests/policy/test_guard.py`: Mock detector, verify routing decisions.
- `tests/policy/test_consent.py`: Verify consent check against DB state.

**Verification:**
- All known sensitive patterns are detected.
- Content with sensitive data returns `allowed_remote: false`.
- Content without sensitive data returns `allowed_remote: true`.
- Missing consent blocks source access.

---

#### Step 1.2.2: Model Router

**Objective:** Route requests to Ollama or OpenAI based on policy decisions and user preferences. Covers FR-33, FR-34, FR-35.

**Changes:**
- Create `backend/src/assistant/routing/` package:
  - `router.py`:
    - `async def invoke(prompt: str, policy_decision: PolicyDecision, settings: UserSettings) -> ModelResponse`
    - If `policy_decision.allowed_remote == False` → always use Ollama.
    - If `allowed_remote == True` → use `settings.routing_preference`.
    - Circuit breaker: if Azure OpenAI fails 3x in 60s, fallback to Ollama for non-sensitive requests.
    - Emit `RoutingEvent` to audit log after every invocation.
  - `providers/ollama.py`:
    - `async def complete(prompt, model) -> str` — calls Ollama chat API via `ollama` Python SDK.
  - `providers/azure_openai_provider.py`:
    - `async def complete(prompt, model) -> str` — calls Azure OpenAI API via `openai` Python SDK (`AzureOpenAI` client).
  - `schemas.py`: `ModelResponse(text: str, model_used: str, provider: str, latency_ms: float)`.

**Unit tests:**
- `tests/routing/test_router.py`: Mock providers; verify sensitive → Ollama, non-sensitive → preferred, fallback on failure.
- `tests/routing/test_ollama.py`: Mock HTTP, verify correct API call shape.
- `tests/routing/test_azure_openai_provider.py`: Mock HTTP, verify correct API call shape.

**Verification:**
- Sensitive content never reaches OpenAI provider.
- Circuit breaker triggers after configured failure threshold.
- Every invocation creates a RoutingEvent audit entry.

---

### Phase 1.3: Integrations

#### Step 1.3.1: Apple Notes Connector

**Objective:** Read and sync notes from Apple Notes via macOS AppleScript bridge. Covers FR-19 through FR-22.

**Changes:**
- Create `backend/src/assistant/integrations/apple_notes/` package:
  - `connector.py`:
    - `async def connect() -> ConnectionResult` — verify AppleScript access.
    - `async def sync_notes(folder_filter: list[str] | None) -> SyncResult` — read notes via osascript, compare with last sync version, upsert/delete in memory service.
    - `async def disconnect() -> None` — revoke consent, stop syncing.
  - `applescript.py`:
    - `def fetch_notes(folder: str | None) -> list[RawNote]` — execute AppleScript to extract note id, title, body, modified date.
    - `def fetch_folders() -> list[str]` — list available folders.
  - `schemas.py`: `RawNote`, `SyncResult`, `ConnectionResult`.
- Create `backend/src/assistant/api/integrations.py`:
  - `POST /v1/integrations/apple-notes/connect`
  - `POST /v1/integrations/apple-notes/sync`
  - `DELETE /v1/integrations/apple-notes/disconnect`
  - `GET /v1/integrations/status` — returns connection status for all integrations.
- Register router in `main.py`.

**Unit tests:**
- `tests/integrations/apple_notes/test_connector.py`: Mock AppleScript output, verify sync creates correct MemoryRecords, updates handle modified notes, deletes handle removed notes.
- `tests/integrations/apple_notes/test_applescript.py`: Mock subprocess, verify command construction and output parsing.

**Verification:**
- Notes are ingested and searchable via retrieval endpoint.
- Modified notes update existing memory records.
- Deleted notes are removed from retrieval index.
- Disconnect stops sync and revokes consent flag.

---

#### Step 1.3.2: Browser Capture Extension

**Objective:** Chrome extension that captures URL/title/selected text and sends to local backend. Covers FR-23 through FR-26.

**Changes:**
- Create `extension/` directory at project root.
  - `manifest.json`: Manifest V3 with:
    - `permissions: ["activeTab", "contextMenus"]`
    - `host_permissions: ["http://localhost:*/"]`
    - `background.service_worker: "background.js"`
  - `background.js`: Service worker:
    - Context menu item "Capture to Assistant".
    - On capture: collect URL, title, selected text from active tab.
    - POST to `http://localhost:{port}/v1/integrations/browser-capture`.
  - `popup.html` + `popup.js`: Minimal UI showing capture status and optional full-page toggle.
  - `content.js`: Content script to extract selected text and optionally full page text.
- Create `backend/src/assistant/integrations/browser/` package:
  - `handler.py`:
    - `async def handle_capture(payload: BrowserCapturePayload) -> CaptureResult`
    - Validates payload, creates MemoryRecord candidate or auto-ingests based on memory mode.
  - `schemas.py`: `BrowserCapturePayload(url, title, selected_text, full_page_content, capture_mode)`.
- Add endpoint in `backend/src/assistant/api/integrations.py`:
  - `POST /v1/integrations/browser-capture`

**Unit tests:**
- `tests/integrations/browser/test_handler.py`: Test capture ingestion in each memory mode (auto/ask/manual).
- Extension: manual testing (Chrome extension testing frameworks are out of unit-test scope).

**Verification:**
- Extension loads in Chrome, context menu appears.
- Capture sends correct payload to local backend.
- Captured content is searchable via retrieval.
- Full-page capture toggle works.

---

### Phase 1.4: Notes Generation and Task Engine

#### Step 1.4.1: Structured Note Generation

**Objective:** Generate structured notes from conversations with edit-before-save. Covers FR-02 through FR-05.

**Changes:**
- Create `backend/src/assistant/notes/` package:
  - `generator.py`:
    - `async def generate_notes(session_id: str) -> GeneratedNotes`
    - Calls model with conversation transcript and structured-output prompt.
    - Returns: summary, decisions, action_items, open_questions.
  - `schemas.py`: `GeneratedNotes(summary, decisions, action_items, open_questions, suggested_tags)`.
- Add to conversation orchestrator: detect note-generation intent commands ("remember this", "save notes", "summarize").
- Add endpoints in `backend/src/assistant/api/chat.py`:
  - `POST /v1/chat/sessions/{session_id}/notes` — generates notes, returns for review.
  - `POST /v1/chat/sessions/{session_id}/notes/save` — saves edited notes as NoteItem + MemoryRecord.

**Unit tests:**
- `tests/notes/test_generator.py`: Mock model response, verify structured output parsing.
- `tests/api/test_chat.py`: Add tests for note generation and save endpoints.

**Verification:**
- Notes are generated with all four sections populated.
- User can edit and save; saved version matches edits.
- Saved notes appear in retrieval results.
- Tags are attached correctly.

---

#### Step 1.4.2: Task Agent / Workflow Engine

**Objective:** Convert user intent into trackable tasks with lifecycle management. Covers FR-27 through FR-30.

**Changes:**
- Create `backend/src/assistant/tasks/` package:
  - `engine.py`:
    - `async def create_task(objective: str, due_context: str | None) -> TaskRecord`
    - `async def update_task(task_id: str, status: str, outcome: str | None) -> TaskRecord`
    - `async def list_tasks(status_filter: str | None) -> list[TaskRecord]`
    - State machine: `created → in_progress → blocked → completed | cancelled`
    - Confirmation gate: if action is classified as high-impact, return `requires_confirmation: true`.
  - `intent_parser.py`:
    - `async def parse_task_intent(message: str) -> TaskIntent | None`
    - Uses model to extract objective, due date hints, and impact level.
  - `schemas.py`: `TaskIntent`, `TaskRecord` Pydantic models.
- Create `backend/src/assistant/api/tasks.py`:
  - `POST /v1/tasks` — create task.
  - `PATCH /v1/tasks/{task_id}` — update status, confirm high-impact.
  - `GET /v1/tasks` — list with optional status filter.
- Register router in `main.py`.
- Integrate intent detection into conversation orchestrator: when task intent is detected, create task and include in response.

**Unit tests:**
- `tests/tasks/test_engine.py`: Test state machine transitions, invalid transitions rejected.
- `tests/tasks/test_intent_parser.py`: Mock model, verify parsing of objectives and due dates.
- `tests/api/test_tasks.py`: TestClient for all task endpoints.

**Verification:**
- Tasks created from conversation flow.
- State transitions follow valid paths only.
- High-impact tasks require confirmation before proceeding.
- Task list returns filtered results.

---

### Phase 1.5: Audit, Settings, and Observability

#### Step 1.5.1: Audit Pipeline

**Objective:** Immutable hash-chained audit trail for all policy and data lifecycle events. Covers FR-35, FR-40, FR-45.

**Changes:**
- Create `backend/src/assistant/audit/` package:
  - `service.py`:
    - `async def log_event(action_type, actor, target_type, target_id, before_state, after_state) -> AuditEvent`
    - Computes `after_hash = sha256(previous_hash + event_json)`.
    - Appends to audit table.
  - `schemas.py`: `AuditEvent`, `AuditQuery`.
  - `integrity.py`:
    - `async def verify_chain(from_event_id: str | None) -> IntegrityResult`
    - Walks chain, verifies each hash.
- Create `backend/src/assistant/api/audit.py`:
  - `GET /v1/audit/events` — search with filters (actor, action_type, target, time range).
  - `GET /v1/audit/integrity` — verify chain integrity.
- Integrate audit logging into: Memory Service (create/update/delete), Routing (every invocation), Settings (every change), Integrations (connect/disconnect/sync).

**Unit tests:**
- `tests/audit/test_service.py`: Log events, verify hash chain integrity.
- `tests/audit/test_integrity.py`: Tamper with event, verify detection.
- `tests/api/test_audit.py`: TestClient for query and integrity endpoints.

**Verification:**
- All specified event types are logged.
- Chain integrity check passes for untampered data.
- Chain integrity check fails when event is modified.

---

#### Step 1.5.2: Settings and Configuration API

**Objective:** User-facing configuration for memory mode, routing, and retrieval preferences. Covers FR-41 through FR-45.

**Changes:**
- Create `backend/src/assistant/api/settings.py`:
  - `GET /v1/settings` — returns all current settings.
  - `PATCH /v1/settings/memory-mode` — sets auto/ask/manual.
  - `PATCH /v1/settings/model-routing` — sets non-sensitive route preference.
  - `PATCH /v1/settings/retrieval` — sets source priority and time horizon.
- Each change:
  - Validates input.
  - Persists to `UserSettings` table.
  - Emits audit event with before/after values.
  - Takes effect immediately (no restart, per NFR-14).
- Register router in `main.py`.

**Unit tests:**
- `tests/api/test_settings.py`: Test each setting change, verify DB update and audit event.

**Verification:**
- Settings changes are reflected in subsequent requests without restart.
- Audit trail captures all setting modifications.

---

#### Step 1.5.3: OpenTelemetry Instrumentation

**Objective:** Local traces and metrics for all key journeys. Covers NFR-11, NFR-12.

**Changes:**
- Create `backend/src/assistant/telemetry/` package:
  - `setup.py`: Configure OpenTelemetry TracerProvider and MeterProvider with local OTLP exporter (file or local collector).
  - `middleware.py`: FastAPI middleware to create spans for every request with `request_id`.
- Add span instrumentation to:
  - Conversation orchestrator (end-to-end respond span).
  - Retrieval service (query span with latency).
  - Policy guard (evaluate span).
  - Model router (invoke span with provider and latency).
  - Memory service (ingest span).
- Add metrics:
  - `assistant.chat.latency` histogram.
  - `assistant.retrieval.latency` histogram.
  - `assistant.routing.decisions` counter by (provider, sensitivity_class).
  - `assistant.memory.operations` counter by (operation, mode).

**Unit tests:**
- `tests/telemetry/test_setup.py`: Verify tracer and meter are created.
- `tests/telemetry/test_middleware.py`: Verify request spans are created.

**Verification:**
- Traces are written to local file/collector.
- Key spans appear for chat, retrieval, routing, and memory flows.
- Metrics are recorded and queryable.

---

### Phase 1.6: Desktop UI Implementation

#### Step 1.6.1: Chat Interface

**Objective:** Functional chat UI with streaming responses, source citations, and memory candidate confirmations.

**Changes:**
- `desktop/src/renderer/pages/Chat.tsx`:
  - Message input and send.
  - Streaming response display.
  - Source attribution badges (clickable to show snippet).
  - Memory candidate confirmation inline (for ask mode).
  - Task creation notification inline.
  - Note generation trigger and edit-before-save modal.
- `desktop/src/renderer/components/`:
  - `MessageBubble.tsx`: User and assistant messages.
  - `SourceBadge.tsx`: Clickable source attribution.
  - `MemoryConfirm.tsx`: Approve/reject pending memory write.
  - `NoteEditor.tsx`: Edit generated notes before save.
  - `TaskCard.tsx`: Task summary with status.

**Unit tests:**
- `desktop/src/__tests__/components/MessageBubble.test.tsx`: Renders user and assistant variants.
- `desktop/src/__tests__/components/SourceBadge.test.tsx`: Renders and expands snippet.

**Verification:**
- Send message → receive grounded response with sources.
- Memory confirmation appears in ask mode.
- Note generation and save flow completes.

---

#### Step 1.6.2: Settings and Integration Panel

**Objective:** Settings UI and integration management panel.

**Changes:**
- `desktop/src/renderer/pages/Settings.tsx`:
  - Memory mode selector (auto/ask/manual).
  - Model routing preference selector.
  - Integration status cards (Apple Notes: connected/disconnected, Browser: installed/not).
  - Sync history and error display.
- `desktop/src/renderer/pages/Memory.tsx`:
  - Memory browser: list, search, filter by source/time.
  - Delete controls: by item, by source, by time range.
- `desktop/src/renderer/pages/Tasks.tsx`:
  - Task list with status filters.
  - Task detail with confirmation actions.

**Unit tests:**
- `desktop/src/__tests__/pages/Settings.test.tsx`: Settings changes call correct API endpoints.

**Verification:**
- Settings persist across app restarts.
- Integration connect/disconnect works.
- Memory deletion removes items from future searches.

---

### Phase 1.7: KPI Instrumentation

#### Step 1.7.1: Evaluation Framework

**Objective:** Local evaluation pipeline for recall accuracy and task completion rate measurement.

**Changes:**
- Create `backend/src/assistant/evaluation/` package:
  - `recall.py`:
    - `async def evaluate_recall(eval_set: list[EvalCase]) -> RecallMetrics`
    - For each case: run retrieval, compare against expected ground truth, score grounding.
  - `tasks.py`:
    - `async def compute_task_completion(time_range) -> TaskCompletionMetrics`
    - Query task lifecycle events, compute completion rate by type.
  - `schemas.py`: `EvalCase`, `RecallMetrics(precision, recall, f1, by_source)`, `TaskCompletionMetrics(rate, by_type, median_cycle_time)`.
- Create `backend/src/assistant/api/evaluation.py`:
  - `POST /v1/evaluation/recall` — run recall evaluation.
  - `GET /v1/evaluation/task-completion` — get task completion metrics.

**Unit tests:**
- `tests/evaluation/test_recall.py`: Seed known memories, verify correct precision/recall computation.
- `tests/evaluation/test_tasks.py`: Seed task records, verify correct completion rate.

**Verification:**
- Recall evaluation produces metrics matching manual calculation.
- Task completion metrics are accurate for test data.

---

## 5) Dependencies and Sequencing

### Dependency Graph

```
Phase 1.0 (Scaffolding)
  ├── 1.0.1 Python Backend ──┐
  ├── 1.0.2 Electron Shell ──┤ (parallel)
  └── 1.0.3 Database Layer ──┘
         │
Phase 1.1 (Core) ─── depends on 1.0
  ├── 1.1.1 Conversation ──── depends on 1.1.2, 1.1.3, 1.2.1, 1.2.2
  ├── 1.1.2 Memory Service ── depends on 1.0.3
  └── 1.1.3 Retrieval ─────── depends on 1.0.3, 1.1.2
         │
Phase 1.2 (Privacy) ─── depends on 1.0
  ├── 1.2.1 Policy Guard ──── independent
  └── 1.2.2 Model Router ──── depends on 1.2.1
         │
Phase 1.3 (Integrations) ─── depends on 1.1.2
  ├── 1.3.1 Apple Notes ───── depends on 1.1.2
  └── 1.3.2 Browser Extension ─ depends on 1.1.2
         │
Phase 1.4 (Notes + Tasks) ─── depends on 1.1.1
  ├── 1.4.1 Note Generation ── depends on 1.1.1, 1.2.2
  └── 1.4.2 Task Engine ────── depends on 1.1.1
         │
Phase 1.5 (Audit + Settings) ─ depends on 1.0.3
  ├── 1.5.1 Audit Pipeline ── independent (wire into other modules incrementally)
  ├── 1.5.2 Settings API ──── depends on 1.0.3
  └── 1.5.3 Telemetry ─────── depends on 1.0.1
         │
Phase 1.6 (UI) ─── depends on all backend APIs
  ├── 1.6.1 Chat UI ─────── depends on 1.1.1, 1.1.2, 1.4.1, 1.4.2
  └── 1.6.2 Settings UI ──── depends on 1.5.2, 1.3
         │
Phase 1.7 (KPI) ─── depends on 1.1.2, 1.1.3, 1.4.2
```

### Parallelizable Work
- 1.0.1, 1.0.2, 1.0.3 can all start simultaneously.
- 1.1.2 Memory + 1.2.1 Policy Guard can proceed in parallel.
- 1.3.1 Apple Notes + 1.3.2 Browser Extension can proceed in parallel.
- 1.5.1 Audit + 1.5.3 Telemetry can start early and be wired incrementally.
- 1.6 UI work can start with mock data while backend stabilizes.

### Ordering Constraints
- Database layer (1.0.3) must complete before any service that persists data.
- Policy Guard (1.2.1) must complete before Model Router (1.2.2).
- Model Router (1.2.2) must complete before Conversation Orchestrator (1.1.1) is fully functional.
- Memory Service (1.1.2) must complete before Integrations (1.3) can ingest data.

---

## 6) Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| AppleScript bridge is fragile across macOS versions | Medium | High | Abstract behind adapter interface; add version detection and graceful degradation; document supported macOS versions |
| SQLCipher + SQLite vector extension compatibility issues | Medium | High | Validate both extensions load in same process during 1.0.3; prepare fallback to separate DBs if needed |
| Ollama model quality insufficient for structured output | Medium | Medium | Use Azure OpenAI for structured outputs (notes, task parsing) when non-sensitive; keep Ollama for simple completions and embeddings |
| Electron + Python sidecar startup reliability | Medium | Medium | Implement health check polling with exponential backoff; add restart logic; surface "backend starting" state in UI |
| Sensitive pattern detector false positives on code snippets | High | Medium | Build curated test set; add per-pattern confidence scores; allow user override with audit logging |
| Browser extension localhost communication blocked by Chrome | Low | High | Use explicit `host_permissions` in manifest; document any Chrome flags needed; test on latest stable Chrome |

---

## 7) Validation Strategy

### Unit Tests
- Target: 80% line coverage for backend `src/assistant/` package.
- Run: `pytest tests/ --cov=assistant --cov-report=term-missing`
- Every module has corresponding `tests/<module>/` directory.
- All service methods have positive and negative path tests.
- Policy detector has comprehensive pattern test matrix.

### Static Checks
- Python: `ruff check src/ tests/` (linting) + `mypy src/` (type checking).
- TypeScript: `tsc --noEmit` (type checking) + ESLint.
- Run all checks in a single `make check` target.

### Manual Verification Checklist (Phase 1 exit)
1. Send chat message → receive grounded response with source badges.
2. Ask mode: memory candidate appears → confirm → searchable in next query.
3. Manual mode: chat produces no memory writes.
4. Paste API key in message → response processed locally by Ollama, audit shows policy block.
5. Connect Apple Notes → notes appear in search results.
6. Browser extension: right-click capture → content searchable.
7. Request notes from session → structured output with summary/decisions/actions/questions.
8. Create task via conversation → task appears in task list → complete and confirm.
9. Delete memory by source → items removed from search.
10. Change settings → immediate effect without restart.
11. Audit trail shows all above actions with intact hash chain.

---

## 8) Definition of Done

### Functional Completeness
- [ ] All 30 Must-priority functional requirements (FR-01 to FR-45 Must subset) are implemented and testable.
- [ ] All 10 Must-priority user stories (US-01 to US-09) pass their Gherkin acceptance criteria.
- [ ] Memory modes auto/ask/manual work correctly with audit trail.
- [ ] Sensitive content is never transmitted to Azure OpenAI (verified by audit log and integration test with pattern samples).
- [ ] Apple Notes and Browser capture data is searchable.

### Quality Gates
- [ ] Unit test coverage >= 80% for backend.
- [ ] `ruff check` passes with zero warnings.
- [ ] `mypy` passes in strict mode.
- [ ] TypeScript compilation passes with zero errors.
- [ ] No known security vulnerabilities in dependencies (`pip audit`, `npm audit`).

### Performance
- [ ] Grounded response latency: median <= 2.5s measured over 20 test queries.
- [ ] Browser capture acknowledgment: <= 2.0s.

### KPI Readiness
- [ ] Recall accuracy evaluation pipeline runs and produces metrics.
- [ ] Task completion rate metric is computed from task lifecycle events.
- [ ] Phase 1 baseline measured: recall accuracy >= 70%, task completion >= 55%.

### Documentation
- [ ] README.md with setup instructions, architecture overview, and development workflow.
- [ ] API documentation auto-generated from FastAPI OpenAPI spec at `/docs`.
- [ ] Each ADR referenced in architecture doc is reflected in implementation.
