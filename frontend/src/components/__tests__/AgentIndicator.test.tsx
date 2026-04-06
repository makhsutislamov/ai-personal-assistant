import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { AgentIndicator } from '../AgentIndicator'

describe('AgentIndicator', () => {
  it('shows when status is working', () => {
    render(<AgentIndicator agentName="file_search" status="working" />)
    expect(screen.getByText(/file_search is working/i)).toBeInTheDocument()
  })

  it('is hidden when status is complete', () => {
    const { container } = render(<AgentIndicator agentName="file_search" status="complete" />)
    expect(container.firstChild).toBeNull()
  })

  it('is hidden when status is error', () => {
    const { container } = render(<AgentIndicator agentName="file_search" status="error" />)
    expect(container.firstChild).toBeNull()
  })

  it('shows agent name in the indicator', () => {
    render(<AgentIndicator agentName="MyAgent" status="working" />)
    expect(screen.getByText(/MyAgent/)).toBeInTheDocument()
  })
})
