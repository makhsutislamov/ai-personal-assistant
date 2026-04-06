import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { InputBar } from '../InputBar'

describe('InputBar', () => {
  it('calls onSend when Enter is pressed with text', () => {
    const onSend = vi.fn()
    render(<InputBar onSend={onSend} />)
    const textarea = screen.getByRole('textbox')
    fireEvent.change(textarea, { target: { value: 'Hello' } })
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false })
    expect(onSend).toHaveBeenCalledWith('Hello')
  })

  it('does not call onSend on Shift+Enter', () => {
    const onSend = vi.fn()
    render(<InputBar onSend={onSend} />)
    const textarea = screen.getByRole('textbox')
    fireEvent.change(textarea, { target: { value: 'Hello' } })
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: true })
    expect(onSend).not.toHaveBeenCalled()
  })

  it('is disabled when disabled prop is true', () => {
    const onSend = vi.fn()
    render(<InputBar onSend={onSend} disabled />)
    const textarea = screen.getByRole('textbox')
    expect(textarea).toBeDisabled()
  })

  it('does not call onSend with empty string', () => {
    const onSend = vi.fn()
    render(<InputBar onSend={onSend} />)
    const textarea = screen.getByRole('textbox')
    fireEvent.change(textarea, { target: { value: '   ' } })
    fireEvent.keyDown(textarea, { key: 'Enter' })
    expect(onSend).not.toHaveBeenCalled()
  })
})
