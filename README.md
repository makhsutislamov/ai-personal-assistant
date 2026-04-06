# AI Personal Assistant

A desktop AI assistant built with Electron, React, and a Python (FastAPI) backend. Supports local models via Ollama and cloud models via Azure OpenAI. Includes a multi-agent architecture for system interactions such as local file search.

---

## Features

- **Conversational chat** with streaming token responses
- **Multi-session** support — create and switch between chat sessions
- **Multi-agent architecture** — the LLM can invoke agents (tools) to interact with your system
  - **File Search Agent** — search your local filesystem by name or glob pattern
- **Dual LLM provider support**
  - [Ollama](https://ollama.com/) — run models locally (default: `llama3.1`)
  - [Azure OpenAI](https://azure.microsoft.com/en-us/products/ai-services/openai-service) — connect to a deployed model
- **Configurable settings** — switch providers and models from the UI, persisted to disk
- **Packaged desktop app** — ships as a macOS DMG (x64 + arm64) via Electron Builder

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  Electron Shell                  │
│  ┌───────────────────┐  ┌──────────────────────┐ │
│  │  React Frontend   │  │   Python Backend     │ │
│  │  (Vite + TS)      │◄─►  (FastAPI + uvicorn) │ │
│  │                   │  │                      │ │
│  │  • ChatWindow     │  │  • Orchestrator      │ │
│  │  • Sidebar        │  │  • Agent Registry    │ │
│  │  • SettingsPanel  │  │  • LLM Providers     │ │
│  └───────────────────┘  │  • Session Store     │ │
│                         └──────────────────────┘ │
└─────────────────────────────────────────────────┘
```

- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS
- **Backend**: Python 3.11+, FastAPI, Pydantic v2, async WebSocket streaming
- **Desktop shell**: Electron 35, communicates backend URL and auth token to renderer via `contextBridge`

---

## Prerequisites

| Requirement | Version |
|---|---|
| Node.js | 18+ |
| Python | 3.11+ |
| npm | 9+ |

For local models:
- [Ollama](https://ollama.com/download) running on `http://localhost:11434`
- At least one model pulled, e.g. `ollama pull llama3.1`

For Azure OpenAI:
- An Azure OpenAI resource with a deployed model
- Endpoint, API key, deployment name, and API version

---

## Setup

### 1. Clone and install Node dependencies

```bash
git clone <repo-url>
cd ai-personal-assistant
npm install
cd frontend && npm install && cd ..
```

### 2. Set up the Python virtual environment

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cd ..
```

---

## Development

Start all three processes (frontend, backend, Electron) with one command:

```bash
./scripts/dev.sh
```

Or start them individually:

```bash
# Terminal 1 — React frontend (Vite HMR)
npm run dev:frontend

# Terminal 2 — Python backend (auto-reload)
npm run dev:backend

# Terminal 3 — Electron shell
npm run dev:electron
```

The backend runs at `http://127.0.0.1:8000`. The frontend dev server runs on a separate port and is loaded by Electron in development mode.

---

## Configuration

Settings are persisted to the platform config directory (e.g. `~/Library/Application Support/ai-personal-assistant/settings.json` on macOS) with owner-only file permissions.

You can configure everything from the **Settings panel** inside the app, or edit `settings.json` directly:

```json
{
  "llm_provider": "ollama",
  "ollama": {
    "base_url": "http://localhost:11434",
    "model": "llama3.1"
  },
  "azure_openai": {
    "endpoint": "https://<resource>.openai.azure.com/",
    "api_key": "<your-key>",
    "deployment": "<deployment-name>",
    "api_version": "2024-02-01"
  }
}
```

### Check available models

```bash
python scripts/get-available-models.py
```

---

## Testing

```bash
# Backend (pytest)
npm run test:backend

# Frontend (Vitest)
npm run test:frontend
```

---

## Building

Build a distributable macOS DMG:

```bash
npm run build
```

This runs in sequence:
1. Compiles Electron TypeScript (`tsconfig.electron.json`)
2. Builds the React frontend (`vite build`)
3. Bundles the Python backend with PyInstaller into `backend/dist/backend/`
4. Packages everything with Electron Builder → `dist-electron/`

The backend binary is bundled as an `extraResource` inside the app and launched by the Electron main process.

---

## Project Structure

```
├── electron/          # Electron main process and preload scripts
├── frontend/          # React application (Vite)
│   └── src/
│       ├── components/    # UI components (ChatWindow, Sidebar, SettingsPanel, …)
│       ├── hooks/         # useChat, useSettings
│       ├── services/      # API client
│       └── types/
├── backend/           # Python FastAPI backend
│   └── app/
│       ├── agents/        # Agent implementations (FileSearchAgent, …)
│       ├── api/           # REST/WebSocket route handlers
│       ├── core/          # Orchestrator, session store, config manager
│       ├── llm/           # LLM provider abstractions (Ollama, Azure OpenAI)
│       └── models/        # Pydantic schemas
├── scripts/           # dev.sh, build-backend.sh, get-available-models.py
├── docs/              # Architecture docs and improvement plans
└── build/             # macOS entitlements for notarization
```

---

## API Overview

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/sessions` | List all chat sessions |
| `POST` | `/api/sessions` | Create a new session |
| `DELETE` | `/api/sessions/{id}` | Delete a session |
| `GET` | `/api/settings` | Get current settings |
| `PUT` | `/api/settings` | Save settings |
| `GET` | `/api/providers/status` | Check LLM provider availability |
| `WebSocket` | `/ws/chat` | Streaming chat (token-by-token) |

---

## License

Private — see `package.json`.
