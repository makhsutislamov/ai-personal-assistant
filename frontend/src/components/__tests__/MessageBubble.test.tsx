import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MessageBubble } from '../MessageBubble'
import type { Message } from '../../types'

describe('MessageBubble', () => {
  it('renders user message with correct alignment class', () => {
    const msg: Message = { id: '1', role: 'user', content: 'Hello world' }
    const { container } = render(<MessageBubble message={msg} />)
    expect(screen.getByText('Hello world')).toBeInTheDocument()
    expect(container.firstChild).toHaveClass('justify-end')
  })

  it('renders assistant message with markdown content', () => {
    const msg: Message = { id: '2', role: 'assistant', content: '**bold text**' }
    const { container } = render(<MessageBubble message={msg} />)
    const bold = container.querySelector('strong')
    expect(bold).toBeInTheDocument()
    expect(bold?.textContent).toBe('bold text')
  })

  it('shows streaming cursor when isStreaming is true', () => {
    const msg: Message = { id: '3', role: 'assistant', content: 'typing...', isStreaming: true }
    const { container } = render(<MessageBubble message={msg} />)
    const cursor = container.querySelector('.animate-pulse')
    expect(cursor).toBeInTheDocument()
  })

  it('does not show cursor when not streaming', () => {
    const msg: Message = { id: '4', role: 'assistant', content: 'done', isStreaming: false }
    const { container } = render(<MessageBubble message={msg} />)
    const cursor = container.querySelector('.animate-pulse')
    expect(cursor).toBeNull()
  })
})
