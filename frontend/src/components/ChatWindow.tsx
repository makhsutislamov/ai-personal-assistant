import React, { useEffect, useRef } from 'react'
import { useChat } from '../hooks/useChat'
import { AgentIndicator } from './AgentIndicator'
import { InputBar } from './InputBar'
import { MessageBubble } from './MessageBubble'

interface ChatWindowProps {
  backendUrl: string
  onNewChat?: () => void
  newChatTrigger?: number
}

export function ChatWindow({ backendUrl, newChatTrigger }: ChatWindowProps) {
  const { messages, isStreaming, activeAgent, error, sendMessage, startNewChat } = useChat(backendUrl)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Trigger new chat when parent requests it
  useEffect(() => {
    if (newChatTrigger && newChatTrigger > 0) {
      startNewChat()
    }
  }, [newChatTrigger, startNewChat])

  return (
    <div className="flex flex-col h-full bg-neutral-900">
      {/* Message area */}
      <div className="flex-1 overflow-y-auto py-4 scrollbar-thin scrollbar-thumb-neutral-700">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-center px-8">
            <div className="w-14 h-14 rounded-2xl bg-teal-600/20 flex items-center justify-center">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-7 h-7 text-teal-400">
                <path fillRule="evenodd" d="M9 4.5a.75.75 0 01.721.544l.813 2.846a3.75 3.75 0 002.576 2.576l2.846.813a.75.75 0 010 1.442l-2.846.813a3.75 3.75 0 00-2.576 2.576l-.813 2.846a.75.75 0 01-1.442 0l-.813-2.846a3.75 3.75 0 00-2.576-2.576l-2.846-.813a.75.75 0 010-1.442l2.846-.813A3.75 3.75 0 007.466 7.89l.813-2.846A.75.75 0 019 4.5z" clipRule="evenodd" />
              </svg>
            </div>
            <div>
              <p className="text-neutral-300 font-medium text-base">How can I help you today?</p>
              <p className="text-neutral-500 text-sm mt-1">
                Ask me anything or say "find all .pdf files in ~/Documents"
              </p>
            </div>
          </div>
        )}

        {messages.map(message => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {activeAgent && (
          <AgentIndicator agentName={activeAgent.name} status={activeAgent.status} />
        )}

        {error && (
          <div className="mx-4 mb-2 px-3 py-2 bg-red-900/30 border border-red-700/30 rounded-xl text-red-400 text-xs">
            Error: {error}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <InputBar onSend={sendMessage} disabled={isStreaming} />
    </div>
  )
}
