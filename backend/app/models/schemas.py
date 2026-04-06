from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    id: str
    type: Literal["function"] = "function"
    function: dict[str, Any]


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None


class UserMessagePayload(BaseModel):
    type: Literal["message"] = "message"
    session_id: str
    content: str


# ---------------------------------------------------------------------------
# Stream events (discriminated union on the `type` field)
# ---------------------------------------------------------------------------


class TokenEvent(BaseModel):
    type: Literal["token"] = "token"
    content: str


class AgentStatusEvent(BaseModel):
    type: Literal["agent_status"] = "agent_status"
    agent_name: str
    status: Literal["working", "complete", "error"]


class AgentResultEvent(BaseModel):
    type: Literal["agent_result"] = "agent_result"
    agent_name: str
    data: Any


class DoneEvent(BaseModel):
    type: Literal["done"] = "done"


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    code: str
    message: str


StreamEvent = TokenEvent | AgentStatusEvent | AgentResultEvent | DoneEvent | ErrorEvent


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


class OllamaSettings(BaseModel):
    base_url: str = "http://localhost:11434"
    model: str = "llama3.1"


class AzureOpenAISettings(BaseModel):
    endpoint: str = ""
    api_key: str = ""
    deployment: str = ""
    api_version: str = "2024-02-01"


class SettingsSchema(BaseModel):
    llm_provider: Literal["ollama", "azure_openai"] = "ollama"
    ollama: OllamaSettings = Field(default_factory=OllamaSettings)
    azure_openai: AzureOpenAISettings = Field(default_factory=AzureOpenAISettings)


# ---------------------------------------------------------------------------
# Provider status
# ---------------------------------------------------------------------------


class ProviderStatus(BaseModel):
    available: bool
    models: list[str] = Field(default_factory=list)


class ProvidersStatusResponse(BaseModel):
    ollama: ProviderStatus
    azure_openai: ProviderStatus


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------


class SessionResponse(BaseModel):
    session_id: str
