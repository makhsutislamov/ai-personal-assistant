import React, { useState } from 'react'
import { ChatWindow } from './components/ChatWindow'
import { Sidebar } from './components/Sidebar'
import { SettingsPanel } from './components/SettingsPanel'

const electronAPI = (window as unknown as { electronAPI?: { backendUrl?: string; authToken?: string } })?.electronAPI
const BACKEND_URL = electronAPI?.backendUrl
  ?? import.meta.env.VITE_BACKEND_URL
  ?? 'http://localhost:8000'
const AUTH_TOKEN = electronAPI?.authToken ?? ''

export default function App() {
  const [showSettings, setShowSettings] = useState(false)
  const [newChatTrigger, setNewChatTrigger] = useState(0)

  const handleNewChat = () => setNewChatTrigger(n => n + 1)

  return (
    <div className="flex h-screen bg-neutral-950 text-neutral-100 overflow-hidden font-sans">
      <Sidebar onNewChat={handleNewChat} onOpenSettings={() => setShowSettings(true)} />
      <main className="flex-1 flex flex-col min-w-0">
        <ChatWindow backendUrl={BACKEND_URL} authToken={AUTH_TOKEN} newChatTrigger={newChatTrigger} />
      </main>
      {showSettings && <SettingsPanel onClose={() => setShowSettings(false)} />}
    </div>
  )
}
