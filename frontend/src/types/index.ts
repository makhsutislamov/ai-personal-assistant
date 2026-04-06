export interface ToolCall {
  id: string
  type: 'function'
  function: {
    name: string
    arguments: string
  }
}

export interface ChatMessage {
  role: 'system' | 'user' | 'assistant' | 'tool'
  content: string | null
  tool_calls?: ToolCall[]
  tool_call_id?: string
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  isStreaming?: boolean
}

// ---------------------------------------------------------------------------
// Stream events
// ---------------------------------------------------------------------------

export interface TokenEvent {
  type: 'token'
  content: string
}

export interface AgentStatusEvent {
  type: 'agent_status'
  agent_name: string
  status: 'working' | 'complete' | 'error'
}

export interface AgentResultEvent {
  type: 'agent_result'
  agent_name: string
  data: unknown
}

export interface DoneEvent {
  type: 'done'
}

export interface ErrorEvent {
  type: 'error'
  code: string
  message: string
}

export type StreamEvent =
  | TokenEvent
  | AgentStatusEvent
  | AgentResultEvent
  | DoneEvent
  | ErrorEvent

// ---------------------------------------------------------------------------
// Settings
// ---------------------------------------------------------------------------

export interface OllamaSettings {
  base_url: string
  model: string
}

export interface AzureOpenAISettings {
  endpoint: string
  api_key: string
  deployment: string
  api_version: string
}

export interface Settings {
  llm_provider: 'ollama' | 'azure_openai'
  ollama: OllamaSettings
  azure_openai: AzureOpenAISettings
}

// ---------------------------------------------------------------------------
// Provider status
// ---------------------------------------------------------------------------

export interface ProviderStatusItem {
  available: boolean
  models: string[]
}

export interface ProviderStatus {
  ollama: ProviderStatusItem
  azure_openai: ProviderStatusItem
}

// ---------------------------------------------------------------------------
// File search result
// ---------------------------------------------------------------------------

export interface FileResult {
  name: string
  path: string
  last_modified: number
  size_bytes: number
}

export interface SessionResponse {
  session_id: string
}
