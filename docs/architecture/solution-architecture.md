**1. Problem Framing**

Source requirements used for this design: [docs/requirements/business-requirements.md](docs/requirements/business-requirements.md).

This architecture targets a desktop-first AI Personal Assistant that maximizes two business KPIs: recall accuracy and task completion rate, while enforcing non-negotiable privacy constraints. The most critical requirement is policy-safe model routing where sensitive data never leaves the user device and is never sent to remote models.

Business and technical goals translated to quality attributes and NFR alignment:

| Goal | Quality Attribute | NFR Mapping | Target | Design Mechanisms |
|---|---|---|---|---|
| Trustworthy recall | Accuracy, Grounding | NFR-01, NFR-02, NFR-07 | Median <= 2.5s, P95 <= 6s, low quality degradation at 10x memory volume | Hybrid retrieval, reranking, confidence gating, source attribution |
| Reliable task execution | Workflow reliability | NFR-04, NFR-05 | 99.5% core availability, >=98% daily ingestion success | Durable task state machine, retries, dead-letter handling |
| Privacy-safe operation | Security, Data minimization | NFR-08, NFR-10 | 0 sensitive remote transmissions, 100% consent enforcement | Policy Guard hard gate, local-only sensitive path, consent checks |
| Strong governance | Auditability, traceability | NFR-11, NFR-12 | 100% model routing logs, >=95% journey coverage | Immutable audit stream, OpenTelemetry traces, policy decision logs |
| Data rights compliance | Deletion and retention | NFR-09 | Delete within 24h | Index-aware deletion workflow + tombstone propagation |
| Usable day-to-day assistant | Usability and speed | NFR-03, NFR-15, NFR-16 | Browser capture <=2s, setup <=15 min, trust >=4/5 | Fast local capture path, guided onboarding, explainable responses |
| Maintainable delivery | Operability and evolvability | NFR-13, NFR-14 | 100% Must requirement traceability, config changes without restart | Modular services, contract-first APIs, hot-reloadable policy config |

Scope enforcement in this design:
1. In scope: conversation assistant, memory/knowledge base, semantic search, Apple Notes integration, browser capture integration, agentic tasks, dual routing (OpenAI + Ollama), memory modes (auto/ask/manual), privacy and audit controls.
2. Out of scope: screenshot workflows and generic active app integrations beyond Notes and browser.

---

**2. Assumptions and Constraints**

Assumptions used:
1. Initial release is single-user and desktop-centric.
2. Apple Notes access is user-authorized and revocable.
3. Browser extension communicates with desktop over localhost secure channel.
4. Evaluation and telemetry remain local by default, with user-initiated export only when explicitly approved.

Hard constraints:
1. Sensitive data classes (passwords, tokens, secrets, private keys, connection strings, and similar) must use local-only path.
2. Sensitive payloads must be blocked before any remote invocation.
3. Retrieval responses should be grounded or explicitly uncertain.
4. Deletion must remove data from active retrieval within 24 hours.

Non-blocking uncertainties:
1. Exact sensitive taxonomy breadth beyond credentials.
2. Retention defaults by source category.
3. Isolation model for work vs personal contexts.

---

**3. Project Stack Inference**

Current repository state is requirements-first with no code implementation yet, so stack inference is moderate-confidence.

Primary inference:
1. Desktop-first mixed architecture strongly favors Electron + TypeScript because it naturally supports local services, browser extension ecosystem, and cross-platform desktop delivery.
2. Local AI inference aligns with Ollama on-device and remote fallback to OpenAI APIs.
3. Fast iteration and stronger AI/retrieval ecosystem support suggest a Python backend (FastAPI) paired with the TypeScript desktop shell and extension integration.

Fallback inference:
1. If Electron is not preferred, the same architecture can be implemented in another runtime while preserving service boundaries and API contracts.
2. Keep provider adapters and domain contracts stable to avoid lock-in.

Recommendation basis:
1. Choose one backend runtime for MVP to reduce integration friction.
2. Preserve contracts so components can be ported across runtimes later.

---

**4. Architecture Options**

**Option A: Local-Only Desktop Monolith**
1. Everything runs on device: orchestration, storage, vector index, policy, task engine, and model calls only to local Ollama.
2. Pros: strongest privacy posture, simplest compliance narrative, offline resilience.
3. Cons: weaker model quality ceiling for some tasks, heavier local compute requirements, limited telemetry centralization.
4. Best when: privacy-first user segment and regulated environments dominate.

**Option B: Desktop-First Hybrid with Policy-Enforced Routing (Recommended)**
1. Core assistant services run locally; sensitive traffic stays local; non-sensitive requests can route to OpenAI.
2. Observability and evaluation pipelines stay local, with optional manual export workflows for reporting.
3. Pros: best balance of KPI performance, privacy enforcement, and delivery speed.
4. Cons: more operational complexity than pure local, requires clear consent and data boundary controls.
5. Best when: product needs both quality and strict privacy guarantees.

**Option C: Cloud-Centric Assistant with Local Privacy Proxy**
1. Most orchestration in cloud, local proxy classifies/redacts before remote calls.
2. Pros: easier centralized operations, easier multi-device sync later.
3. Cons: highest trust risk, complex redaction correctness burden, weaker offline behavior.
4. Best when: enterprise multi-tenant scale is immediate priority.

Comparative trade-off summary:

| Criterion | Option A | Option B | Option C |
|---|---|---|---|
| Delivery speed | Medium | Medium-High | Medium |
| Privacy assurance | Very High | High | Medium |
| Recall quality potential | Medium | High | High |
| Operational complexity | Low-Medium | Medium | High |
| Cost at MVP | Low | Medium | Medium-High |
| Scale path | Medium | High | High |
| Fit to requirements | High | Very High | Medium |

---

**5. Recommended Target Architecture**

Target style: modular local backend with event-driven internal workflows, wrapped by a desktop application, with policy-first model routing and local-first observability.

Rationale:
1. Meets strict local-only sensitive path requirement by design.
2. Preserves low-latency local operations for memory and capture.
3. Enables higher answer quality using remote models for non-sensitive requests.
4. Keeps migration path open from MVP to scaled hybrid operations.

Core module design (implementation-oriented):

| Module | Responsibilities | Inputs/Outputs | Failure Handling | Scale Strategy |
|---|---|---|---|---|
| Conversation Orchestrator | Session state, prompt assembly, clarification flow, response composition | Input: user message, session context. Output: grounded response, source list, action prompts | Graceful uncertainty response when retrieval confidence is low | Stateless compute with local session cache |
| Memory Service | Ingest, normalize, dedupe, classify, retain, delete, source reconciliation | Input: candidate memory, integration payloads. Output: canonical memory records + embeddings + audit events | Retry queue for failed ingest, explicit status for user | Batch ingestion worker with backpressure |
| Retrieval Service | Semantic search, lexical fallback, reranking, grounding package build | Input: query + filters. Output: ranked evidence bundle | Timeout fallback to lexical-only path | ANN index shard per source and time partition |
| Integration Services | Apple Notes sync and browser capture validation/edit-before-save | Input: source API events or extension capture. Output: normalized SourceDocument and MemoryRecord candidates | Per-source retry policies, sync checkpoints | Adapter pattern per integration connector |
| Task Agent / Workflow Engine | Intent-to-task conversion, state transitions, confirmation gates, completion summaries | Input: user objective. Output: TaskRecord lifecycle events | Durable retries, compensation actions, dead-letter queue | Workflow workers with deterministic state machine |
| Policy Guard | Sensitivity detection, DLP policy checks, consent enforcement, outbound guardrails | Input: messages, candidates, model requests. Output: allow/block + route constraints | Block-on-uncertainty and notify user | Rules engine with model-assisted classifier fallback |
| Model Router | Route to Ollama/OpenAI, fallback logic, cost/latency policy | Input: policy result + request profile. Output: model invocation and routing event | Circuit breaker + local fallback on remote errors | Pluggable provider adapters |
| Audit/Observability Pipeline | Immutable audit chain, metrics, traces, redacted logs export | Input: domain events from all modules. Output: searchable audit and telemetry | Local durable spool and bounded retention | Asynchronous event pipeline |

Security and privacy architecture embedded in runtime:
1. Trust Boundary 1: browser extension to desktop localhost API with signed short-lived tokens.
2. Trust Boundary 2: desktop local services and encrypted local data stores.
3. Trust Boundary 3: outbound network boundary to OpenAI only.
4. Enforcement Point A: pre-ingest sensitivity classification.
5. Enforcement Point B: pre-model invocation Policy Guard hard stop.
6. Enforcement Point C: consent validation before source sync and retrieval exposure.
7. Enforcement Point D: telemetry redaction before export.

Reliability and performance design targets by request path:

| Path | Latency Budget | Strategy |
|---|---|---|
| Browser capture acknowledge | <= 2.0s | Write-ahead local queue + async enrichment |
| Typical grounded query | Median <= 2.5s | Embedding cache + ANN retrieval + compact context pack |
| Heavy grounded query | P95 <= 6.0s | Two-stage retrieval + rerank timeout budget |
| Sensitive local route | <= 3.5s P95 | Local model pool warm-up + prompt compression |
| Task create/update | <= 1.5s ack | Async workflow execution with immediate status event |

Caching, retry, idempotency:
1. Query embedding cache keyed by normalized query hash and time window.
2. Retrieval result cache for repeated queries with invalidation on new writes.
3. Exponential backoff with jitter for integration and remote model calls.
4. Idempotency keys for capture ingest, task transitions, and delete operations.

---

**6. C4-Style Component View**

Context view:

~~~mermaid
flowchart LR
    U[User] --> D[AI Personal Assistant Desktop App]
    B[Browser Extension] --> D
    N[Apple Notes] --> D
    D --> O[Ollama Local Runtime]
    D --> A[OpenAI API]
  D --> E[Local Eval and Telemetry Store]
    D --> S[Local Encrypted Data Stores]
~~~

Container view:

~~~mermaid
flowchart TB
    subgraph Device["User Device Trust Boundary"]
      UI[Desktop UI]
      API[Local Backend API]
      ORCH[Conversation Orchestrator]
      MEM[Memory Service]
      RET[Retrieval Service]
      TASK[Task Workflow Engine]
      POL[Policy Guard]
      ROUTE[Model Router]
      AUD[Audit and Telemetry Collector]
      DB[(Operational DB)]
      VDB[(Vector Index)]
      LOG[(Immutable Audit Store)]
      OLL[Ollama Runtime]
      EXT[Browser Extension Connector]
      NOTES[Apple Notes Connector]
    end

    UI --> API
    API --> ORCH
    ORCH --> RET
    ORCH --> TASK
    ORCH --> POL
    POL --> ROUTE
    ROUTE --> OLL
    ROUTE --> OPENAI[OpenAI API]
    MEM --> DB
    MEM --> VDB
    MEM --> LOG
    RET --> VDB
    EXT --> MEM
    NOTES --> MEM
    TASK --> DB
    AUD --> LOG
    API --> AUD
    MEM --> AUD
    RET --> AUD
    ROUTE --> AUD
    AUD --> LOG
~~~

Component view for core backend:

| Component | Key Internals | Critical Interactions |
|---|---|---|
| Conversation Orchestrator | Session manager, prompt builder, confidence gate | Calls Retrieval Service, Policy Guard, Model Router |
| Memory Service | Normalizer, deduper, retention manager, delete processor | Receives integration events and user save actions |
| Retrieval Service | Query planner, ANN retriever, lexical retriever, reranker, grounding assembler | Returns evidence bundle and confidence score |
| Task Workflow Engine | Intent parser, state machine, confirmation gate, completion reporter | Emits task lifecycle events and summary payloads |
| Policy Guard | PII/secret detector, outbound validator, consent verifier | Enforces local-only sensitive route decisions |
| Model Router | Provider adapters, fallback policy, circuit breaker | Chooses Ollama or OpenAI and records route event |
| Audit Pipeline | Hash-chain event writer, OTel exporter, redaction processor | Receives events from all core services |

---

**7. Interface and Data Contracts**

Storage architecture:

| Data Class | Primary Store | Rationale | Alternative |
|---|---|---|---|
| Operational entities (sessions, tasks, settings, consent) | SQLite with WAL + SQLCipher encryption | Strong local reliability and encrypted-at-rest data on-device | PostgreSQL local container in hybrid advanced mode |
| Semantic vectors and retrieval metadata | SQLite vector extension for MVP; Qdrant local for scale-up | Smaller desktop footprint first, then stronger ANN/filtering scale path | pgvector when moving to centralized hybrid store |
| Audit and event log | Append-only local log + hash chain | Tamper-evident governance trail | Object storage with immutability lock in hybrid |
| Telemetry metrics/traces | Local OpenTelemetry collector spool | Resilient when offline | Direct export to managed observability backend |

Core entities and indexes:
1. MemoryRecord: memoryId, sourceType, sourceRef, canonicalText, sensitivityClass, confidence, createdAt, updatedAt, deletedAt.
2. SourceDocument: sourceId, externalRef, title, syncVersion, syncStatus, consentSnapshot.
3. BrowserCapture: captureId, url, title, selectedText, fullPageContentRef, captureMode, createdAt.
4. TaskRecord: taskId, objective, owner, dueAt, status, blockedReason, completionOutcome.
5. RoutingEvent: eventId, requestId, sensitivityDecision, chosenModel, blockReason, latencyMs.
6. AuditEvent: eventId, actor, actionType, targetType, targetId, beforeHash, afterHash, createdAt.

Recommended indexes:
1. MemoryRecord composite index on sourceType + updatedAt.
2. MemoryRecord partial index on deletedAt is null for active retrieval.
3. TaskRecord index on status + dueAt.
4. RoutingEvent index on createdAt + sensitivityDecision.
5. Vector HNSW index on embedding with filterable metadata for source and time.

High-level API contracts:

| Domain | Endpoint/Event | Purpose |
|---|---|---|
| Chat | POST /v1/chat/respond | Returns grounded response with source attributions and model path metadata |
| Chat | GET /v1/chat/sessions/{sessionId} | Fetches session transcript and notes context |
| Memory | POST /v1/memory/candidates | Creates candidate memory item (Ask/Manual flow) |
| Memory | POST /v1/memory/confirm | Confirms or rejects candidate write |
| Memory | DELETE /v1/memory | Deletes by item, source, or time range |
| Retrieval | POST /v1/retrieval/query | Executes semantic search with source/time filters |
| Integrations | POST /v1/integrations/apple-notes/connect | Starts consented connection |
| Integrations | POST /v1/integrations/apple-notes/sync | Triggers sync/reconciliation |
| Integrations | POST /v1/integrations/browser-capture | Accepts extension capture payload |
| Tasks | POST /v1/tasks | Creates task from intent/objective |
| Tasks | PATCH /v1/tasks/{taskId} | Updates status and confirmations |
| Settings | PATCH /v1/settings/memory-mode | Sets auto/ask/manual |
| Settings | PATCH /v1/settings/model-routing | Sets non-sensitive route preference |
| Audit | GET /v1/audit/events | Searches exportable audit trail |

Key events (internal bus):
1. MemoryCandidateCreated
2. MemoryWriteConfirmed
3. MemoryDeleted
4. SourceSyncCompleted
5. PolicyBlockedRemoteRoute
6. ModelInvocationCompleted
7. TaskStateChanged
8. SettingsChanged

Data lifecycle and deletion workflow:
1. Ingest receives candidate and runs normalization, sensitivity classification, dedupe score, and user confirmation if required.
2. Persist writes canonical record and embedding in one local transaction with audit event.
3. Retention job marks expired records, removes vectors, and emits deletion-complete events.
4. User deletion by source/time creates tombstones immediately, removes from active retrieval index, and completes physical purge asynchronously within SLA.

Telemetry and KPI instrumentation:
1. Recall accuracy pipeline: sample grounded responses, attach evidence set, human-review labels, compute weekly precision by source and sensitivity class.
2. Task completion pipeline: track started, blocked, completed, accepted outcome states; compute completion rate and median cycle time.
3. Trace model includes request_id spanning ingest, retrieval, policy, routing, and generation.
4. Privacy-preserving telemetry stays local by default and supports user-initiated redacted export artifacts.

---

**8. Key Decisions (ADR Style)**

ADR-001  
Context: Need strict privacy with high model quality.  
Decision: Desktop-first hybrid with mandatory local core and local-first observability.  
Consequences: Strong privacy-by-default with quality gains for non-sensitive requests; moderate integration complexity.

ADR-002  
Context: Sensitive data must never be sent remote.  
Decision: Policy Guard as hard pre-routing gate with block-on-uncertainty.  
Consequences: Eliminates accidental remote leak path; may increase false positives initially.

ADR-003  
Context: Need scalable retrieval quality and speed.  
Decision: Two-stage retrieval (vector + lexical) with reranking and confidence threshold.  
Consequences: Better recall precision and grounding; extra compute cost for reranking.

ADR-004  
Context: Users need control over memory pollution.  
Decision: Implement memory modes auto, ask, manual as first-class persisted policy.  
Consequences: Higher trust and controllability; more UX branching complexity.

ADR-005  
Context: Deduplication required without losing nuance.  
Decision: Hybrid dedupe using exact hash + near-duplicate embedding threshold + source heuristics.  
Consequences: Cleaner knowledge base; risk of over-merging mitigated by review logs.

ADR-006  
Context: Task completion KPI depends on durable workflows.  
Decision: Task engine implemented as durable state machine with idempotent commands.  
Consequences: Reliable progress tracking and recovery; higher implementation effort than ad-hoc tasks.

ADR-007  
Context: Governance requires tamper-evident audit.  
Decision: Append-only hash-chained audit events with export API.  
Consequences: Strong audit integrity; adds storage overhead and verification tooling.

ADR-008  
Context: Need observability without privacy leakage.  
Decision: OpenTelemetry with redaction pipeline and policy-level event coverage mandates.  
Consequences: High operational visibility; requires strict log schema governance.

ADR-009  
Context: Local storage must be secure by default.  
Decision: Encrypt operational DB and secrets via OS keychain-backed keys.  
Consequences: Better endpoint security posture; key rotation and backup logic needed.

ADR-010  
Context: Need migration path from MVP to scale.  
Decision: Keep stable domain APIs and provider adapters so stores and model providers are swappable.  
Consequences: Lower long-term lock-in; requires upfront contract discipline.

---

**9. Risks and Mitigations**

1. Risk: Sensitive-data classifier misses edge cases.  
Mitigation: Conservative policy, deny on ambiguity, continuous evaluation set with adversarial samples.

2. Risk: Overly strict blocking harms usability.  
Mitigation: User-visible reason codes, local model fallback, tuning loop on false positive labels.

3. Risk: Retrieval latency grows with data volume.  
Mitigation: Source/time partitioning, ANN tuning, rerank budget caps, cache hit-rate SLO.

4. Risk: Sync drift between Apple Notes and index.  
Mitigation: Version checkpoints, periodic reconciliation, drift alarms, replayable sync jobs.

5. Risk: Confirmation fatigue lowers task completion.  
Mitigation: Risk-based confirmation tiers and user-configurable thresholds for low-impact actions.

6. Anti-pattern: Sending whole conversation to remote model by default.  
Mitigation: Context minimization and policy scrubber before outbound requests.

7. Anti-pattern: Using mutable audit logs.  
Mitigation: Append-only hash chain and periodic integrity verification.

8. Risk: KPI instrumentation bias due non-representative samples.  
Mitigation: Stratified sampling across sources, sensitivity class, and task complexity.

---

**10. Delivery Roadmap**

Phase blueprint:

| Phase | Build Scope | Exit Validation |
|---|---|---|
| Phase 1 (MVP) | Conversation Orchestrator, Memory Service baseline, Apple Notes + browser capture, Policy Guard v1, Model Router, basic Retrieval Service, Task engine v1, audit + telemetry baseline | Recall accuracy >=70%, task completion >=55%, zero sensitive remote transmissions, Must requirements pass |
| Phase 2 (Quality and Governance) | Retrieval reranking, dedupe improvements, richer task workflows, full audit coverage, deletion and retention automation, settings and control panel maturity | Recall >=80%, task completion >=68%, full routing telemetry and deletion SLA compliance |
| Phase 3 (Scale and Hardening) | Performance tuning at 10x data, advanced policy taxonomy, reliability hardening, usability refinements, advanced local evaluation automation | Recall >=88%, task completion >=78%, stable NFR performance and governance metrics |

MVP to scaled migration strategy:
1. Start local-first with adapter interfaces for model providers, vector store, and telemetry exporters.
2. Expand local evaluation and reporting pipelines with optional user-approved export artifacts.
3. Add centralized non-sensitive backup/sync later using the same domain events and consent controls.
4. Keep API versioning from day one to avoid breaking extension and desktop clients.

Validation and governance checkpoints:
1. Architecture spike: sensitivity detector benchmark and false-positive/false-negative profile.
2. Load test: retrieval latency at 1x, 5x, 10x memory volume.
3. Security checks: outbound traffic policy tests and secret leak red-team scenarios.
4. Observability baseline: trace coverage >=95% on capture/retrieval/task flows.
5. Go/no-go gates at end of each phase aligned with KPI thresholds and privacy incidents count.

Operational readiness:
1. SLOs: grounded response latency, ingestion success, policy violation count, delete SLA.
2. Alerting: sync drift, policy block spikes, model provider failure rates, queue backlogs.
3. Incident ownership: privacy incidents highest severity with immediate local-only fail-safe mode.
4. Runbooks: integration reconnect, index rebuild, model outage fallback, audit integrity verification.

---

**11. Clarification Needed**

Blocking confirmations:
1. Sensitive taxonomy launch scope: credentials-only or include financial/legal/health/confidential business classes at MVP.
2. Default deployment mode: local-only by default with opt-in hybrid, or hybrid enabled by default with explicit consent.

Non-blocking but important:
1. Retention defaults by source and class (conversation, notes, browser captures, tasks, audit).
2. Work/personal separation approach: strict profile isolation vs tag-and-filter MVP.
3. Grounding policy UX: hard block ungrounded responses or allow with warning in low-risk contexts.
4. Apple Notes handling for locked/protected notes at launch.
5. Definition of high-impact action tiers for task confirmations.
6. Human evaluation ownership and weekly labeling budget for KPI measurement.
7. Approval workflow and retention policy for user-initiated telemetry export artifacts.

---

**12. Recommended Tech Stack (Primary + Alternatives)**

Primary stack (recommended for fastest delivery and best requirement fit):
1. Desktop app shell: Electron + TypeScript + React, with contextIsolation + preload + contextBridge IPC boundary.
2. Local backend services: Python FastAPI + Uvicorn, using Pydantic schemas for strict request and policy contracts.
3. Local operational DB: SQLite (WAL) + SQLCipher, with key wrapping via Electron safeStorage backed by macOS Keychain.
4. Vector store: SQLite vector extension for MVP; Qdrant local when dataset size/filter complexity requires stronger ANN behavior.
5. Workflow engine: Durable SQLite-backed state machine queue for MVP (no extra infra); Celery/RQ only for hybrid or server mode where Redis is acceptable.
6. Local LLM runtime: Ollama.
7. Remote LLM provider: OpenAI Responses API (streaming and structured outputs enabled where needed).
8. Telemetry: OpenTelemetry Python SDK (backend) + OpenTelemetry JS (desktop shell) + local collector agent mode.
9. Secrets: macOS Keychain for API keys and encryption key wrapping.
10. Browser extension: Manifest V3 extension using service worker + explicit host_permissions + signed localhost communication.

Alternative A (Local-only privacy-max):
1. Remove OpenAI remote path entirely at MVP.
2. Use only Ollama with model portfolio tuning.
3. Keep same architecture modules but simplify outbound network controls.
4. Trade-off: stronger privacy posture, likely lower recall/task quality for complex reasoning until local models improve.