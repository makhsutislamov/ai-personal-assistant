import type { ProviderStatus, SessionResponse, Settings } from '../types'

const BASE_URL = (window as unknown as { electronAPI?: { backendUrl?: string } })?.electronAPI?.backendUrl
  ?? import.meta.env.VITE_BACKEND_URL
  ?? 'http://localhost:8000'

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`API error ${response.status}: ${errorText}`)
  }
  return response.json() as Promise<T>
}

export async function createSession(): Promise<SessionResponse> {
  return apiFetch<SessionResponse>('/api/sessions', { method: 'POST' })
}

export async function deleteSession(sessionId: string): Promise<void> {
  await apiFetch<unknown>(`/api/sessions/${sessionId}`, { method: 'DELETE' })
}

export async function getSettings(): Promise<Settings> {
  return apiFetch<Settings>('/api/settings')
}

export async function updateSettings(settings: Settings): Promise<Settings> {
  return apiFetch<Settings>('/api/settings', {
    method: 'PUT',
    body: JSON.stringify(settings),
  })
}

export async function getProviderStatus(): Promise<ProviderStatus> {
  return apiFetch<ProviderStatus>('/api/settings/providers/status')
}

export function createChatWebSocket(sessionId: string, token?: string): WebSocket {
  const wsBase = BASE_URL.replace(/^http/, 'ws')
  const url = token
    ? `${wsBase}/ws/chat?session_id=${sessionId}&token=${token}`
    : `${wsBase}/ws/chat?session_id=${sessionId}`
  return new WebSocket(url)
}
