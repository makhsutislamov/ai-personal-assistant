import { vi } from 'vitest'

export const useSettings = vi.fn(() => ({
  settings: {
    llm_provider: 'ollama' as const,
    ollama: { base_url: 'http://localhost:11434', model: 'llama3.1' },
    azure_openai: { endpoint: '', api_key: '', deployment: '', api_version: '2024-02-01' },
  },
  providerStatus: null,
  loading: false,
  error: null,
  loadSettings: vi.fn(),
  saveSettings: vi.fn(),
  checkProviderStatus: vi.fn(),
}))
