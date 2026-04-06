import React from 'react'

interface AgentIndicatorProps {
  agentName: string
  status: 'working' | 'complete' | 'error'
}

export function AgentIndicator({ agentName, status }: AgentIndicatorProps) {
  if (status === 'complete' || status === 'error') return null

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-teal-900/40 border border-teal-600/30 text-teal-300 text-xs w-fit mx-4 mb-2">
      <span className="relative flex h-2 w-2">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-teal-400 opacity-75" />
        <span className="relative inline-flex rounded-full h-2 w-2 bg-teal-500" />
      </span>
      <span>{agentName} is working…</span>
    </div>
  )
}
