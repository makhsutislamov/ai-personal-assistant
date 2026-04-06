import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createSession, getSettings, updateSettings } from '../api'

const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

function mockResponse(data: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
  }
}

describe('API service', () => {
  beforeEach(() => {
    mockFetch.mockReset()
  })

  it('createSession sends POST and parses response', async () => {
    mockFetch.mockResolvedValue(mockResponse({ session_id: 'abc-123' }))
    const result = await createSession()
    expect(result.session_id).toBe('abc-123')
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/sessions'),
      expect.objectContaining({ method: 'POST' })
    )
  })

  it('getSettings returns typed settings', async () => {
    const settings = {
      llm_provider: 'ollama',
      ollama: { base_url: 'http://localhost:11434', model: 'llama3.1' },
      azure_openai: { endpoint: '', api_key: '', deployment: '', api_version: '2024-02-01' },
    }
    mockFetch.mockResolvedValue(mockResponse(settings))
    const result = await getSettings()
    expect(result.llm_provider).toBe('ollama')
    expect(result.ollama.model).toBe('llama3.1')
  })

  it('updateSettings sends PUT with body', async () => {
    const settings = {
      llm_provider: 'azure_openai' as const,
      ollama: { base_url: 'http://localhost:11434', model: 'llama3.1' },
      azure_openai: { endpoint: 'https://test.openai.azure.com/', api_key: 'key', deployment: 'gpt-4o', api_version: '2024-02-01' },
    }
    mockFetch.mockResolvedValue(mockResponse(settings))
    const result = await updateSettings(settings)
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/settings'),
      expect.objectContaining({ method: 'PUT', body: expect.any(String) })
    )
    expect(result.llm_provider).toBe('azure_openai')
  })

  it('throws on non-ok response', async () => {
    mockFetch.mockResolvedValue(mockResponse({ detail: 'Not found' }, 404))
    await expect(createSession()).rejects.toThrow('API error 404')
  })
})
