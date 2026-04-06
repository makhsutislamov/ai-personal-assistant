import '@testing-library/jest-dom'
import { vi, afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'

// Mock react-syntax-highlighter to avoid loading its huge bundle in tests
vi.mock('react-syntax-highlighter', () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  Prism: ({ children }: { children: any }) => children,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  default: ({ children }: { children: any }) => children,
}))
vi.mock('react-syntax-highlighter/dist/esm/styles/prism', () => ({
  oneDark: {},
}))
vi.mock('react-syntax-highlighter/dist/cjs/styles/prism', () => ({
  oneDark: {},
}))

// Stub fetch globally to prevent real network calls in tests
const mockSettings = {
  llm_provider: 'ollama',
  ollama: { base_url: 'http://localhost:11434', model: 'llama3.1' },
  azure_openai: { endpoint: '', api_key: '', deployment: '', api_version: '2024-02-01' },
}
vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
  ok: true,
  status: 200,
  json: async () => mockSettings,
  text: async () => JSON.stringify(mockSettings),
}))

// Mock WebSocket globally
class MockWebSocket {
  static OPEN = 1
  static CLOSED = 3
  readyState = MockWebSocket.OPEN
  onopen: (() => void) | null = null
  onmessage: ((e: MessageEvent) => void) | null = null
  onerror: (() => void) | null = null
  onclose: (() => void) | null = null

  send = vi.fn()
  close = vi.fn()
}

vi.stubGlobal('WebSocket', MockWebSocket)

// Ensure DOM is cleaned up after each test
afterEach(() => {
  cleanup()
})
