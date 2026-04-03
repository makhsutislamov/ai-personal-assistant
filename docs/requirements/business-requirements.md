# AI Personal Assistant - Business Requirements

Date: 2026-04-03

## 1) Product Vision and Problem Statement

Vision: Deliver an interactive AI Personal Assistant that acts like a trusted day-to-day partner for work and personal routines by capturing context, remembering what matters, and helping users complete tasks with high recall accuracy and dependable outcomes.

Problem statement: Users lose time and quality because key information is fragmented across conversations, notes, and browsing activity. Existing assistants often fail to recall prior context, provide ungrounded answers, or mishandle sensitive information. The product closes this gap by combining fast semantic memory retrieval, assistant-like behavior, and privacy-safe model routing.

Business outcomes:
1. Increase user trust through accurate recall and grounded responses.
2. Improve user productivity through higher task completion rate.
3. Reduce context-switching and repeated information entry.
4. Enforce privacy controls so sensitive information remains local.

## 2) Stakeholders, Personas, and Jobs-to-be-Done

| Stakeholder/Persona | Primary Jobs-to-be-Done | Business Value |
|---|---|---|
| Knowledge Worker (primary user) | Capture discussion notes, retrieve prior context quickly, complete tasks with assistant support | Productivity gains, reduced rework |
| Manager/Team Lead | Convert meetings into actionable items, track completion, reduce missed follow-ups | Better execution and accountability |
| Privacy-Conscious User | Ensure secrets stay local and controllable | Trust, adoption, risk reduction |
| Product Owner | Improve recall accuracy and task completion KPIs | Measurable product success |
| Compliance/Security Stakeholder | Ensure governance, auditable actions, and controlled data handling | Risk management, policy alignment |

## 3) Scope Definition

### In Scope
1. Conversational assistant behavior with note-taking from discussions.
2. Memory and knowledge base with semantic search and fast retrieval.
3. Integrations: Apple Notes and Browser capture.
4. Browser capture fields: URL, title, selected text, optional full-page extracted content.
5. Agentic task support for planning, tracking, and completion assistance.
6. Dual model availability with routing across OpenAI and local Ollama.
7. Privacy policy enforcement that keeps sensitive information local.
8. Configurable memory write behavior: auto, ask, manual.
9. KPI focus on recall accuracy and task completion rate.

### Out of Scope
1. Generic active app integrations beyond Apple Notes and Browser.
2. Screenshot capture workflows.
3. Broad enterprise multi-tenant administration features.

### Assumptions
1. Product is primarily single-user oriented in initial phases.
2. Users consent to connect Apple Notes and Browser capture features.
3. Sensitive information taxonomy can be translated into enforceable policy categories.
4. Users accept clarification prompts when confidence is low.

### Constraints
1. Sensitive information must never be sent to remote models.
2. Response speed must remain fast despite retrieval and grounding.
3. Requirements must support both personal and work contexts without data leakage.
4. Scope prioritizes recall accuracy and task completion over feature breadth.

### Dependencies
1. Reliable access permissions for Apple Notes integration.
2. Browser capture permission model and extraction consistency.
3. Availability of OpenAI and local Ollama model paths.
4. Labeled evaluation data for ongoing KPI measurement.

## 4) Functional Requirements

### 4.1 Conversation and Notes

| ID | Description | Priority | Rationale |
|---|---|---|---|
| FR-01 | Assistant supports multi-turn conversations with context continuity within a session. | Must | Core assistant behavior |
| FR-02 | Assistant generates structured notes on request: summary, decisions, action items, open questions. | Must | Real-assistant behavior |
| FR-03 | User can review and edit generated notes before saving. | Must | Accuracy and control |
| FR-04 | Assistant supports explicit note commands such as remember this and save this context. | Must | Intent clarity |
| FR-05 | Notes support tags/categories at save time (work, personal, project). | Should | Better retrieval |

### 4.2 Memory Ingestion and Knowledge Base

| ID | Description | Priority | Rationale |
|---|---|---|---|
| FR-06 | System ingests memory from conversations, Apple Notes, and browser captures into one knowledge base. | Must | Cross-source recall |
| FR-07 | Each memory item stores source metadata, timestamps, and sensitivity classification. | Must | Traceability and governance |
| FR-08 | System supports memory write modes: auto, ask, manual. | Must | Explicit product requirement |
| FR-09 | Ask mode requires explicit user confirmation before persistence. | Must | Prevent memory pollution |
| FR-10 | Manual mode writes nothing without explicit save action. | Must | Strict user control |
| FR-11 | System detects near-duplicate memory items to reduce clutter. | Should | Retrieval quality |
| FR-12 | Ingestion failures are surfaced with status and retry option. | Must | Reliability |

### 4.3 Semantic Retrieval and Grounded Responses

| ID | Description | Priority | Rationale |
|---|---|---|---|
| FR-13 | Assistant performs semantic retrieval across all in-scope sources. | Must | Recall objective |
| FR-14 | Responses using recalled facts include source attribution. | Must | Trust and verification |
| FR-15 | Assistant prioritizes grounded answers over speculative responses. | Must | Quality and safety |
| FR-16 | If confidence is below threshold, assistant asks clarifying questions. | Must | Reduce hallucinations |
| FR-17 | User can inspect retrieved snippets used in answer composition. | Should | Validation speed |
| FR-18 | Retrieval supports filtering by source and time range. | Should | Precision |

### 4.4 Apple Notes Integration

| ID | Description | Priority | Rationale |
|---|---|---|---|
| FR-19 | System supports user-authorized connection to Apple Notes. | Must | In-scope integration |
| FR-20 | System ingests selected notes/folders and keeps them searchable. | Must | Utility |
| FR-21 | System reconciles creates/updates/deletes and updates retrieval index. | Must | Consistency |
| FR-22 | User can disconnect Apple Notes and stop future sync anytime. | Must | Privacy control |

### 4.5 Browser Capture Integration

| ID | Description | Priority | Rationale |
|---|---|---|---|
| FR-23 | User can capture URL, page title, and selected text into memory. | Must | Core scope |
| FR-24 | User can optionally include full-page extracted content. | Must | Scope decision |
| FR-25 | Captured browser items are reviewable/editable before save. | Should | Data quality |
| FR-26 | Captured browser data is retrievable with semantic search and metadata filters. | Must | End-to-end value |

### 4.6 Agentic Task Execution

| ID | Description | Priority | Rationale |
|---|---|---|---|
| FR-27 | Assistant converts intent into explicit tasks with owner, due context, and status. | Must | Task completion KPI |
| FR-28 | Assistant provides progress updates and completion summaries. | Must | Execution visibility |
| FR-29 | Assistant requests confirmation before high-impact actions. | Must | Safety |
| FR-30 | On failure, assistant presents next-best options. | Should | Resilience |

### 4.7 Model Routing (OpenAI and Ollama)

| ID | Description | Priority | Rationale |
|---|---|---|---|
| FR-31 | System classifies inputs/outputs for sensitivity before model invocation. | Must | Privacy enforcement |
| FR-32 | Sensitive content is processed locally only; no remote model transmission. | Must | Non-negotiable requirement |
| FR-33 | Non-sensitive requests follow configurable routing preferences. | Must | Control and cost/perf tuning |
| FR-34 | Assistant can disclose model path on user request. | Should | Transparency |
| FR-35 | Routing decisions and policy blocks are audit logged. | Must | Governance |

### 4.8 Privacy, Security, and Governance

| ID | Description | Priority | Rationale |
|---|---|---|---|
| FR-36 | System provides source-level consent controls for each integration. | Must | Compliance and trust |
| FR-37 | System supports deletion by item, source, and time range. | Must | Data rights and hygiene |
| FR-38 | Policy-impacting controls are restricted to account owner role. | Should | Governance readiness |
| FR-39 | Secrets are blocked from remote transmission and user is notified. | Must | Privacy safeguard |
| FR-40 | Immutable audit trail is kept for policy and data lifecycle events. | Must | Accountability |

### 4.9 Configuration and Admin Controls

| ID | Description | Priority | Rationale |
|---|---|---|---|
| FR-41 | User configures memory mode (auto, ask, manual). | Must | Explicit requirement |
| FR-42 | User configures model routing preference for non-sensitive requests. | Must | Control |
| FR-43 | User configures default retrieval preferences (source priority, time horizon). | Should | Relevance optimization |
| FR-44 | User has control panel for integration status, sync history, and errors. | Should | Operability |
| FR-45 | Settings changes are logged with actor, timestamp, and before/after values. | Must | Governance and troubleshooting |

## 5) Non-Functional Requirements

| ID | Category | Requirement | Target |
|---|---|---|---|
| NFR-01 | Performance | Grounded response latency for typical queries | Median <= 2.5s |
| NFR-02 | Performance | Grounded response latency for heavy queries | P95 <= 6.0s |
| NFR-03 | Performance | Browser capture acknowledgment | <= 2.0s |
| NFR-04 | Reliability | Core assistant availability | >= 99.5% monthly |
| NFR-05 | Reliability | Successful ingestion/sync operations | >= 98% daily success |
| NFR-06 | Reliability | Confirmed memory write durability | 0 confirmed-write loss incidents |
| NFR-07 | Scalability | Retrieval quality under memory growth | <= 20% latency increase at 10x volume |
| NFR-08 | Security | Sensitive-content remote transmission | 0 policy-violating transmissions |
| NFR-09 | Privacy | User deletion request processing | <= 24 hours |
| NFR-10 | Privacy | Data source consent enforcement | 100% source access tied to active consent |
| NFR-11 | Observability | Routing decision telemetry coverage | 100% model calls logged |
| NFR-12 | Observability | Key journey monitoring coverage | >= 95% for capture/retrieval/task flows |
| NFR-13 | Maintainability | Requirement-to-test traceability | 100% of Must requirements mapped |
| NFR-14 | Maintainability | Policy/config updates | No session reset for standard changes |
| NFR-15 | Usability | New user setup time | <= 15 minutes to first successful retrieval |
| NFR-16 | Usability | User trust rating in pilot | >= 4.0/5 |

## 6) User Stories and Gherkin Acceptance Criteria

### Prioritized User Stories

| ID | Story | Priority |
|---|---|---|
| US-01 | As a user, I want grounded answers from my saved context so I can trust recall. | Must |
| US-02 | As a user, I want structured notes from discussions so I can avoid manual documentation overhead. | Must |
| US-03 | As a user, I want memory mode control (auto/ask/manual) so I choose what is remembered. | Must |
| US-04 | As a user, I want Apple Notes searchable in conversation so existing notes become actionable. | Must |
| US-05 | As a user, I want to capture URL/title/selected text from browser so web research is reusable. | Must |
| US-06 | As a user, I want optional full-page capture so I can preserve full context when needed. | Must |
| US-07 | As a user, I want requests converted into trackable tasks so I complete work reliably. | Must |
| US-08 | As a privacy-focused user, I want sensitive content processed locally only so secrets stay protected. | Must |
| US-09 | As a user, I want deletion by item/source/time so I can manage privacy and relevance. | Must |
| US-10 | As a user, I want transparent routing and policy behavior so I understand how outputs are produced. | Should |

### Gherkin Criteria

1. Given relevant memory exists, when the user asks a related question, then the assistant returns a grounded answer with source attribution.
2. Given no relevant memory exists, when the user asks a factual question, then the assistant states uncertainty and asks for clarification or additional sources.
3. Given an ongoing discussion, when the user asks for notes, then the assistant returns summary, decisions, action items, and open questions.
4. Given generated notes are displayed, when the user edits content before save, then the saved version matches user edits.
5. Given memory mode is Ask, when a write candidate appears, then explicit confirmation is required before save.
6. Given memory mode is Manual, when no explicit save command is provided, then no memory write occurs.
7. Given Apple Notes is connected, when sync runs, then new and updated notes become searchable.
8. Given a synced note is deleted at source, when reconciliation runs, then deleted content is no longer retrievable.
9. Given user selects browser text, when capture is triggered, then URL/title/selection are stored as one retrievable item.
10. Given capture review is shown, when user cancels, then no browser item is persisted.
11. Given full-page capture is enabled, when save succeeds, then extracted page content is attached to the capture item.
12. Given full-page extraction fails, when user saves, then basic capture is saved and failure is reported.
13. Given user asks to complete an objective, when intent is parsed, then a task is created with status and due context.
14. Given a task requires high-impact action, when execution is attempted, then explicit confirmation is required first.
15. Given sensitive content is detected, when routing is evaluated, then remote invocation is blocked and local processing is used.
16. Given a routing block occurs, when response is returned, then user sees that privacy policy was enforced.
17. Given user requests deletion by source/time, when deletion is confirmed, then matching memory is removed from retrieval within SLA.
18. Given deletion completes, when audit history is viewed, then deletion event includes actor and timestamp.
19. Given a response is returned, when user asks for processing path, then assistant discloses model path and policy filtering status.
20. Given routing preference is changed, when settings are saved, then eligible future requests follow updated routing.

## 7) Data Requirements

### Core Entities and Key Fields

| Entity | Key Fields |
|---|---|
| UserProfile | userId, profileType, preferences, consentStatus |
| ConversationSession | sessionId, timestamps, topicTags |
| NoteItem | noteId, source, content, tags, sensitivityLevel, timestamps |
| MemoryRecord | memoryId, canonicalText, sourceRef, confidence, sensitivityClass, retentionStatus |
| SourceDocument | sourceId, type, title, externalRef, syncStatus |
| BrowserCapture | captureId, url, title, selectedText, fullPageFlag, fullPageContent, tags, timestamp |
| TaskRecord | taskId, objective, owner, dueDate, status, completionOutcome |
| RetrievalEvent | query, retrievedItems, ranking, groundingFlag, latency |
| RoutingEvent | requestType, sensitivityDecision, modelPath, blockOrAllow |
| AuditEvent | eventId, actor, actionType, targetId, beforeAfter, timestamp |

### Retention and Deletion Rules

1. Retention policy is configurable by data category.
2. User deletion supports item-level and bulk source/date-range operations.
3. Deleted data is removed from active retrieval within SLA.
4. Consent revocation immediately halts future ingestion from that source.
5. Audit records are retained per governance policy with minimum required metadata.

### Audit Logging Requirements

1. Log all memory create/update/delete actions.
2. Log integration connect/disconnect and sync outcomes.
3. Log routing and policy block decisions.
4. Log task lifecycle actions.
5. Log configuration changes with actor/time/effective values.
6. Audit trail must be searchable, exportable, and tamper-evident.

## 8) Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Sensitive-data misclassification | Privacy breach risk | Conservative policy, block-on-uncertainty, periodic review |
| Memory pollution | Reduced recall accuracy | Ask/manual modes, edit-before-save, deduplication |
| Ungrounded responses | Trust erosion | Grounding requirement, confidence gating |
| Sync drift | Stale or missing context | Sync monitoring and reconciliation |
| Confirmation fatigue | Lower usability | Configurable modes and sensible defaults |
| Task ambiguity | Lower completion rate | Structured task schema and confirmation step |
| Poor KPI data quality | Misleading decisions | Labeling protocol and regular metric validation |
| Scope creep | Delayed outcomes | Strict phase gates tied to Must requirements |

## 9) KPI Framework and Measurement Plan

### Primary KPI 1: Recall Accuracy
Definition: Percent of factual recall responses that are both correct and source-grounded.
Formula: Correct grounded recall responses / total evaluated factual recall responses.

Measurement plan:
1. Build recurring evaluation set from anonymized real queries and curated scenarios.
2. Run weekly sampled human review of grounded outputs.
3. Track by source type and sensitivity class.
4. Targets:
   - Phase 1 exit: >= 70%
   - Phase 2 exit: >= 80%
   - Phase 3 exit: >= 88%

### Primary KPI 2: Task Completion Rate
Definition: Percent of user-started tasks completed to user-accepted outcome within expected time window.
Formula: Completed accepted tasks / total started tasks.

Measurement plan:
1. Capture lifecycle events for created, in-progress, blocked, completed.
2. Segment by task type and complexity.
3. Weekly trend review with failure reason taxonomy.
4. Targets:
   - Phase 1 exit: >= 55%
   - Phase 2 exit: >= 68%
   - Phase 3 exit: >= 78%

Supporting indicators:
1. Grounded response coverage.
2. Sensitive-routing block rate and false positives.
3. User correction rate after assistant output.
4. Median grounded-query latency.

## 10) Phased Delivery Plan

| Phase | Focus | Entry Criteria | Exit Criteria |
|---|---|---|---|
| Phase 1 | Core assistant, memory foundation, Apple Notes and browser basic capture, sensitive-local routing baseline | Must-requirements baseline approved, policy definitions drafted, KPI instrumentation plan approved | Must subset accepted, minimum NFRs met, Recall Accuracy >= 70%, Task Completion >= 55% |
| Phase 2 | Retrieval quality uplift, stronger task workflows, richer controls and governance visibility | Phase 1 KPI baseline stable for two reporting cycles | Recall Accuracy >= 80%, Task Completion >= 68%, full audit coverage |
| Phase 3 | Optimization, scale readiness, usability refinements, policy hardening | Phase 2 quality and governance goals met | Recall Accuracy >= 88%, Task Completion >= 78%, retention/deletion and observability targets consistently met |

## 11) Open Decisions

1. Sensitive taxonomy at launch: credentials-only or broader confidential-data classes?
2. Default retention periods by source type.
3. Deletion scope: indexed memory only or stored raw capture copies as well?
4. Grounding strictness: block ungrounded responses by default or permit with warning?
5. Task completion policy when external user action is required.
6. Work/personal separation model: strict profile isolation or tags/filters only for MVP?
7. Apple Notes locked/protected note handling at launch.
8. Human evaluation budget and ownership for weekly labeling cadence.

## MVP Definition

MVP must ship all of the following:
1. Multi-turn assistant conversations with structured note generation and edit-before-save.
2. Unified memory ingestion from conversations, Apple Notes, and browser capture.
3. Browser capture at minimum supports URL, title, selected text; optional full-page extraction available.
4. Semantic retrieval with grounded responses and source attribution.
5. Configurable memory write modes: auto, ask, manual.
6. Agentic task creation, tracking, and completion summaries with confirmation for high-impact actions.
7. Sensitivity-aware routing that enforces local-only handling for sensitive information.
8. Core privacy controls: source consent, deletion by item/source/time, auditable policy/data events.
9. KPI instrumentation for recall accuracy and task completion rate tied to Phase 1 thresholds.

## Immediate Next Steps

1. Approve open decisions to lock Phase 1 acceptance criteria.
2. Convert Must requirements into implementation backlog with estimates.
3. Define test plan mapping each Must requirement to functional and non-functional validation.
