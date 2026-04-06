import { useCallback, useEffect, useRef, useState } from 'react'
import type { AgentStatusEvent, Message, StreamEvent } from '../types'
import { createChatWebSocket, createSession, deleteSession } from '../services/api'

interface ActiveAgent {
  name: string
  status: 'working' | 'complete' | 'error'
}

interface UseChatReturn {
  messages: Message[]
  isStreaming: boolean
  activeAgent: ActiveAgent | null
  error: string | null
  sessionId: string | null
  sendMessage: (content: string) => void
  startNewChat: () => void
}

const MAX_RETRIES = 5

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`
}

export function useChat(backendUrl: string, authToken?: string): UseChatReturn {
  const [messages, setMessages] = useState<Message[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [activeAgent, setActiveAgent] = useState<ActiveAgent | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [sessionId, setSessionId] = useState<string | null>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const retriesRef = useRef(0)
  const sessionIdRef = useRef<string | null>(null)
  const currentAssistantIdRef = useRef<string | null>(null)

  const connect = useCallback((sid: string) => {
    if (wsRef.current) {
      // Null out onclose before intentionally closing to prevent a spurious retry
      wsRef.current.onclose = null
      wsRef.current.close()
    }

    const ws = createChatWebSocket(sid, authToken)
    wsRef.current = ws

    ws.onopen = () => {
      retriesRef.current = 0
      setError(null)
    }

    ws.onmessage = (event: MessageEvent) => {
      try {
        const streamEvent: StreamEvent = JSON.parse(event.data as string)

        if (streamEvent.type === 'token') {
          const token = streamEvent.content
          setMessages(prev => {
            const last = prev[prev.length - 1]
            if (last && last.role === 'assistant' && last.isStreaming) {
              return [
                ...prev.slice(0, -1),
                { ...last, content: last.content + token },
              ]
            }
            const newId = generateId()
            currentAssistantIdRef.current = newId
            return [
              ...prev,
              { id: newId, role: 'assistant', content: token, isStreaming: true },
            ]
          })
          setIsStreaming(true)
        } else if (streamEvent.type === 'agent_status') {
          const agentEvent = streamEvent as AgentStatusEvent
          setActiveAgent({ name: agentEvent.agent_name, status: agentEvent.status })
          if (agentEvent.status === 'complete' || agentEvent.status === 'error') {
            setTimeout(() => setActiveAgent(null), 1500)
          }
        } else if (streamEvent.type === 'done') {
          setMessages(prev =>
            prev.map(m =>
              m.isStreaming ? { ...m, isStreaming: false } : m
            )
          )
          setIsStreaming(false)
          setActiveAgent(null)
          currentAssistantIdRef.current = null
        } else if (streamEvent.type === 'error') {
          setError(streamEvent.message)
          setIsStreaming(false)
        }
      } catch {
        // Ignore parse errors
      }
    }

    ws.onerror = () => {
      setError('Connection error')
    }

    ws.onclose = () => {
      if (retriesRef.current < MAX_RETRIES && sessionIdRef.current) {
        const delay = Math.pow(2, retriesRef.current) * 500
        retriesRef.current += 1
        setTimeout(() => {
          if (sessionIdRef.current) {
            connect(sessionIdRef.current)
          }
        }, delay)
      }
    }
  }, [authToken])

  const initSession = useCallback(async () => {
    try {
      const { session_id } = await createSession()
      sessionIdRef.current = session_id
      setSessionId(session_id)
      connect(session_id)
    } catch (err) {
      setError('Failed to create session')
    }
  }, [connect])

  useEffect(() => {
    initSession()
    return () => {
      wsRef.current?.close()
    }
  }, [initSession])

  const sendMessage = useCallback((content: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      setError('Not connected')
      return
    }
    const sid = sessionIdRef.current
    if (!sid) return

    setMessages(prev => [
      ...prev,
      { id: generateId(), role: 'user', content },
    ])
    setIsStreaming(true)
    setError(null)

    wsRef.current.send(
      JSON.stringify({ type: 'message', session_id: sid, content })
    )
  }, [])

  const startNewChat = useCallback(async () => {
    wsRef.current?.close()
    if (sessionIdRef.current) {
      try {
        await deleteSession(sessionIdRef.current)
      } catch {
        // Best-effort
      }
    }
    setMessages([])
    setIsStreaming(false)
    setActiveAgent(null)
    setError(null)
    sessionIdRef.current = null
    await initSession()
  }, [initSession])

  return { messages, isStreaming, activeAgent, error, sessionId, sendMessage, startNewChat }
}
