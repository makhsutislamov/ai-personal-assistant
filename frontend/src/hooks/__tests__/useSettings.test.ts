import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { useSettings } from '../useSettings'

const mockGetSettings = vi.fn()
const mockUpdateSettings = vi.fn()
const mockGetProviderStatus = vi.fn()

vi.mock('../../services/api', () => ({
  getSettings: () => mockGetSettings(),
  updateSettings: (s: unknown) => mockUpdateSettings(s),
  getProviderStatus: () => mockGetProviderStatus(),
}))

const defaultSettings = {
  llm_provider: 'ollama' as const,
  ollama: { base_url: 'http://localhost:11434', model: 'llama3.1' },
  azure_openai: { endpoint: '', api_key: '', deployment: '', api_version: '2024-02-01' },
}

describe('useSettings', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetSettings.mockResolvedValue(defaultSettings)
  })

  it('loads settings on mount', async () => {
    const { result } = renderHook(() => useSettings())
    await waitFor(() => expect(result.current.settings).not.toBeNull())
    expect(result.current.settings?.llm_provider).toBe('ollama')
  })

  it('saveSettings sends correct payload and updates state', async () => {
    const updated = { ...defaultSettings, llm_provider: 'azure_openai' as const }
    mockUpdateSettings.mockResolvedValue(updated)

    const { result } = renderHook(() => useSettings())
    await waitFor(() => expect(result.current.settings).not.toBeNull())

    await act(async () => {
      await result.current.saveSettings(updated)
    })

    expect(mockUpdateSettings).toHaveBeenCalledWith(updated)
    expect(result.current.settings?.llm_provider).toBe('azure_openai')
  })
})
