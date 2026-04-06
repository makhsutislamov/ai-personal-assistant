# AI Personal Assistant — Business Requirements

## Refined Requirements Summary

**Essential Business Need:** A cross-platform desktop AI assistant that orchestrates multiple specialized agents through a conversational chat interface, starting with file search capability, powered by a user-configurable LLM backend (local via Ollama or cloud via Azure OpenAI).

**Stakeholders:**
- End-user (desktop user seeking AI-assisted productivity)
- Product owner (defining agent expansion roadmap)

**Success Criteria:**
- User can hold multi-turn conversations with context retained within a session (no cross-session persistence in MVP)
- Orchestrator transparently delegates to the correct agent and **visibly indicates which agent is active**
- File search agent finds files by name/path across all directories on the local machine
- Chat UI is responsive, intuitive, and comparable in quality to Claude/ChatGPT desktop experiences
- Application runs on macOS, Windows, and Linux
- User can switch between Ollama (local) and Azure OpenAI (cloud) as the LLM provider

**Assumptions (explicitly marked):**
- *Assumption:* Conversation history is not persisted across sessions; closing the app clears context. Persistence is deferred to a future iteration.
- *Assumption:* Only one specialized agent (file search) is in scope for MVP; the architecture must support registering additional agents over time.
- *Assumption:* File search covers all directories including system folders — no exclusions.
- *Assumption:* "Configure LLM provider" means a settings screen or configuration where the user selects Ollama or Azure OpenAI and provides any required connection details (endpoint, API key for Azure; model name for Ollama).
- *Assumption:* Agent status visibility means an in-chat indicator (e.g., "File Search Agent is working…") — not a separate dashboard.

**Constraints:**
- Must be cross-platform (macOS, Windows, Linux).
- Chat UI must meet modern UX standards (streaming responses, markdown rendering, clear turn separation).
- Must support at least two LLM backends: Ollama (local) and Azure OpenAI (cloud).

**Dependencies:**
- Ollama installed locally for local model usage.
- Azure OpenAI resource provisioned for cloud usage.

---

## Task Breakdown

| # | Business Task | Description |
|---|---|---|
| 1 | **Conversational chat experience** | User can send messages and receive streamed AI responses in a polished chat interface. |
| 2 | **Multi-turn context continuity** | The assistant remembers prior messages within the current session to provide coherent follow-ups. |
| 3 | **Intent-based agent delegation with visibility** | The orchestrator detects when a user request requires a specialized agent, delegates automatically, and shows the user which agent is handling the request. |
| 4 | **Local file search by name/path** | User can ask the assistant to find files on their computer by file name or path and receive actionable results. |
| 5 | **LLM provider configuration** | User can choose between Ollama (local) and Azure OpenAI (cloud) and provide necessary connection settings. |
| 6 | **Cross-platform availability** | The application installs and runs natively on macOS, Windows, and Linux. |
| 7 | **Extensible agent registration** | New agents can be added to the system without reworking the orchestrator. |

---

## User Stories

### Story 1 — Conversational Chat
> As an end-user, I want to chat with an AI assistant in a responsive desktop window, so that I can get help quickly without leaving my desktop workflow.

**Priority: Must**

### Story 2 — Multi-Turn Context
> As an end-user, I want the assistant to remember what I said earlier in the conversation, so that I don't have to repeat context in follow-up messages.

**Priority: Must**

### Story 3 — File Search via Chat
> As an end-user, I want to ask the assistant to find files on my computer by name or path, so that I can locate documents without manually browsing folders.

**Priority: Must**

### Story 4 — Agent Activity Visibility
> As an end-user, I want to see which agent is handling my request while it's in progress, so that I understand what the assistant is doing on my behalf.

**Priority: Must**

### Story 5 — LLM Provider Configuration
> As an end-user, I want to choose between a local model (Ollama) and a cloud model (Azure OpenAI), so that I can balance privacy, cost, and quality based on my preference.

**Priority: Must**

### Story 6 — Cross-Platform Access
> As an end-user, I want to install and use the assistant on macOS, Windows, or Linux, so that I'm not locked to a single operating system.

**Priority: Must**

---

## Acceptance Criteria

### Story 1 — Conversational Chat
1. **Given** the application is launched, **when** the user types a message and presses Enter/Send, **then** the assistant responds within the chat window with a streamed reply.
2. **Given** the assistant is generating a response, **when** the user observes the chat, **then** tokens appear incrementally (streaming), not as a single delayed block.
3. **Given** the chat window is resized, **when** the width changes, **then** the layout adapts responsively without content clipping or overflow.
4. **Given** the assistant returns a response with formatting (lists, code, bold), **when** the user views it, **then** markdown is rendered correctly.

### Story 2 — Multi-Turn Context
5. **Given** the user has sent 3+ messages in a session, **when** the user references "the file I mentioned earlier," **then** the assistant correctly resolves the reference from prior turns.
6. **Given** a conversation is in progress, **when** the user starts a new session (e.g., "New Chat"), **then** previous context is cleared and the assistant starts fresh.
7. **Given** the user closes and reopens the application, **when** a new session begins, **then** no prior conversation history is loaded (persistence is out of scope for MVP).

### Story 3 — File Search via Chat
8. **Given** the user asks "find all PDF files in my Documents folder," **when** the orchestrator processes the request, **then** the file search agent is invoked and returns matching file paths based on file name/path matching.
9. **Given** matching files exist, **when** results are displayed, **then** each result shows the file name, full path, and last modified date.
10. **Given** no files match the search criteria, **when** results are returned, **then** the assistant communicates "no results found" clearly.
11. **Given** the user requests a search in a non-existent directory, **when** the agent processes it, **then** a user-friendly error message is shown (no raw stack traces).
12. **Given** the user asks to search across all directories (including system folders), **when** the agent processes it, **then** all accessible directories are included in the search scope.

### Story 4 — Agent Activity Visibility
13. **Given** the orchestrator delegates to the file search agent, **when** the agent begins processing, **then** the chat displays an indicator such as "File Search Agent is working…"
14. **Given** an agent completes its task, **when** the result is returned, **then** the indicator is replaced by the agent's response.
15. **Given** the user asks a general question handled by the orchestrator directly, **when** no agent is invoked, **then** no agent indicator is shown.

### Story 5 — LLM Provider Configuration
16. **Given** the user opens settings, **when** they select "Ollama" as the provider, **then** the assistant uses the locally running Ollama instance for all inference.
17. **Given** the user opens settings, **when** they select "Azure OpenAI" as the provider and enter a valid endpoint and API key, **then** the assistant uses Azure OpenAI for all inference.
18. **Given** the user selects Ollama but Ollama is not running, **when** the user sends a message, **then** a clear error message indicates the local model is unavailable.
19. **Given** the user selects Azure OpenAI but provides invalid credentials, **when** the user sends a message, **then** a clear error message indicates authentication failed.
20. **Given** the user changes the provider mid-session, **when** the next message is sent, **then** the new provider is used while conversation context is preserved.

### Story 6 — Cross-Platform Access
21. **Given** a macOS, Windows, or Linux machine, **when** the user installs the application, **then** it launches and all core features (chat, file search, provider config) function identically.

---

## Additional BA Outputs

### MVP vs. Future Scope

| Slice | Includes |
|-------|----------|
| **MVP** | Chat UI, multi-turn context (in-session only), orchestrator with agent delegation + agent activity indicator, file search agent (name/path, all directories), LLM provider config (Ollama / Azure OpenAI), macOS + Windows + Linux builds |
| **Iteration 2** | Conversation history persistence and session resume |
| **Future** | Additional agents (calendar, email, terminal, etc.), file content search, themes/settings panel, additional LLM providers |

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| File search across all directories (including system) may be slow or hit permission errors | Poor UX, incomplete results | Show progress indicator; gracefully skip inaccessible directories with a summary note |
| Ollama model quality varies significantly by model choice | Inconsistent assistant behaviour across providers | Document recommended models; surface model selection in settings |
| Cross-platform parity gaps | Features work on one OS but not others | Test on all three platforms per release |

### Data Considerations
- Conversation data stays local and is ephemeral (cleared on app close).
- File search results are never sent to external services without user awareness (if using cloud LLM, the query is sent but file contents are not).
- Azure OpenAI credentials are provided via environment configuration (e.g., environment variables or a local config file).
- No user data telemetry unless opt-in.
