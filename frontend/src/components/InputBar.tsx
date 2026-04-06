import React, { useCallback, useEffect, useRef } from 'react'

interface InputBarProps {
  onSend: (content: string) => void
  disabled?: boolean
}

export function InputBar({ onSend, disabled = false }: InputBarProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    textareaRef.current?.focus()
  }, [])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        const value = textareaRef.current?.value.trim()
        if (value && !disabled) {
          onSend(value)
          if (textareaRef.current) textareaRef.current.value = ''
          // Reset height
          if (textareaRef.current) textareaRef.current.style.height = 'auto'
        }
      }
    },
    [disabled, onSend]
  )

  const handleInput = useCallback(() => {
    const el = textareaRef.current
    if (el) {
      el.style.height = 'auto'
      el.style.height = `${Math.min(el.scrollHeight, 200)}px`
    }
  }, [])

  const handleSendClick = useCallback(() => {
    const value = textareaRef.current?.value.trim()
    if (value && !disabled) {
      onSend(value)
      if (textareaRef.current) textareaRef.current.value = ''
      if (textareaRef.current) textareaRef.current.style.height = 'auto'
    }
  }, [disabled, onSend])

  return (
    <div className="flex items-end gap-3 p-4 border-t border-neutral-800 bg-neutral-950">
      <textarea
        ref={textareaRef}
        rows={1}
        disabled={disabled}
        onKeyDown={handleKeyDown}
        onInput={handleInput}
        placeholder="Type a message… (Enter to send, Shift+Enter for newline)"
        className="flex-1 resize-none rounded-xl bg-neutral-800 border border-neutral-700
          text-neutral-100 placeholder-neutral-500 px-4 py-3 text-sm leading-relaxed
          focus:outline-none focus:ring-2 focus:ring-teal-500/50 focus:border-teal-600
          disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-150
          min-h-[48px] max-h-[200px] overflow-y-auto"
      />
      <button
        onClick={handleSendClick}
        disabled={disabled}
        aria-label="Send message"
        className="flex-shrink-0 w-11 h-11 flex items-center justify-center rounded-xl
          bg-teal-600 hover:bg-teal-500 disabled:opacity-40 disabled:cursor-not-allowed
          cursor-pointer transition-all duration-150 active:scale-95"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5 text-white">
          <path d="M3.478 2.405a.75.75 0 00-.926.94l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.517 60.517 0 003.478 2.405z" />
        </svg>
      </button>
    </div>
  )
}
