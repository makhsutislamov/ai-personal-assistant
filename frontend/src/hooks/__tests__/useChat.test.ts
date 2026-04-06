import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { useChat } from '../useChat'

const mockCreateSession = vi.fn()
const mockDeleteSession = vi.fn()
const mockCreateChatWebSocket = vi.fn()

vi.mock('../../services/api', () => ({
  createSession: () => mockCreateSession(),
  deleteSession: (id: string) => mockDeleteSession(id),
  createChatWebSocket: (sid: string) => mockCreateChatWebSocket(sid),
}))

// Fake WebSocket
class FakeWS {
  static OPEN = 1
  readyState = FakeWS.OPEN
  onopen: (() => void) | null = null
  onmessage: ((e: { data: string }) => void) | null = null
  onerror: (() => void) | null = null
  onclose: (() => void) | null = null
  send = vi.fn()
  close = vi.fn()

  triggerMessage(data: object) {
    this.onmessage?.({ data: JSON.stringify(data) })
  }

  triggerOpen() {
    this.onopen?.()
  }
}

describe('useChat', () => {
  let fakeWs: FakeWS

  beforeEach(() => {
    vi.clearAllMocks()
    fakeWs = new FakeWS()
    mockCreateSession.mockResolvedValue({ session_id: 'test-session-123' })
    mockCreateChatWebSocket.mockReturnValue(fakeWs)
    mockDeleteSession.mockResolvedValue(undefined)
  })

  it('sendMessage sends correct JSON over WebSocket', async () => {
    const { result } = renderHook(() => useChat('http://localhost:8000'))
    await waitFor(() => expect(result.current.sessionId).toBe('test-session-123'))

    act(() => {
      result.current.sendMessage('Hello')
    })

    expect(fakeWs.send).toHaveBeenCalledWith(
      JSON.stringify({ type: 'message', session_id: 'test-session-123', content: 'Hello' })
    )
  })

  it('token events accumulate in message content', async () => {
    const { result } = renderHook(() => useChat('http://localhost:8000'))
    await waitFor(() => expect(result.current.sessionId).not.toBeNull())

    act(() => {
      result.current.sendMessage('Test')
    })

    act(() => {
      fakeWs.triggerMessage({ type: 'token', content: 'Hello' })
    })

    act(() => {
      fakeWs.triggerMessage({ type: 'token', content: ' world' })
    })

    const assistantMsg = result.current.messages.find(m => m.role === 'assistant')
    expect(assistantMsg?.content).toBe('Hello world')
  })

  it('agent_status events update activeAgent state', async () => {
    const { result } = renderHook(() => useChat('http://localhost:8000'))
    await waitFor(() => expect(result.current.sessionId).not.toBeNull())

    act(() => {
      fakeWs.triggerMessage({ type: 'agent_status', agent_name: 'file_search', status: 'working' })
    })

    expect(result.current.activeAgent).toEqual({ name: 'file_search', status: 'working' })
  })

  it('done event finalizes message', async () => {
    const { result } = renderHook(() => useChat('http://localhost:8000'))
    await waitFor(() => expect(result.current.sessionId).not.toBeNull())

    act(() => {
      result.current.sendMessage('Test')
    })

    act(() => {
      fakeWs.triggerMessage({ type: 'token', content: 'Reply' })
    })

    act(() => {
      fakeWs.triggerMessage({ type: 'done' })
    })

    const msg = result.current.messages.find(m => m.role === 'assistant')
    expect(msg?.isStreaming).toBe(false)
    expect(result.current.isStreaming).toBe(false)
  })
})
