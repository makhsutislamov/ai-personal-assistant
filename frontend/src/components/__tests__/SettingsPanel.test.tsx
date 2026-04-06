import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, act } from '@testing-library/react'
import { SettingsPanel } from '../SettingsPanel'

// SettingsPanel renders with DEFAULT_SETTINGS (ollama preset) before API load,
// so we can test the UI without mocking useSettings. The fetch global is stubbed
// in setup.ts to prevent real network calls.

describe('SettingsPanel', () => {
  const onClose = vi.fn()

  beforeEach(() => {
    onClose.mockReset()
  })

  it('renders provider options', async () => {
    await act(async () => {
      render(<SettingsPanel onClose={onClose} />)
    })
    expect(screen.getByText(/Ollama/i)).toBeInTheDocument()
    expect(screen.getByText(/Azure OpenAI/i)).toBeInTheDocument()
  })

  it('shows Ollama fields when Ollama is selected', async () => {
    await act(async () => {
      render(<SettingsPanel onClose={onClose} />)
    })
    expect(screen.getByLabelText(/Base URL/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Model/i)).toBeInTheDocument()
  })

  it('shows Azure fields when Azure OpenAI is selected', async () => {
    await act(async () => {
      render(<SettingsPanel onClose={onClose} />)
    })
    const azureBtn = screen.getAllByText(/Azure OpenAI/i)[0]
    await act(async () => {
      fireEvent.click(azureBtn)
    })
    expect(screen.getByLabelText(/Endpoint/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/API Key/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Deployment/i)).toBeInTheDocument()
  })

  it('calls onClose when Cancel is clicked', async () => {
    await act(async () => {
      render(<SettingsPanel onClose={onClose} />)
    })
    const cancelBtn = screen.getByText('Cancel')
    fireEvent.click(cancelBtn)
    expect(onClose).toHaveBeenCalled()
  })
})
