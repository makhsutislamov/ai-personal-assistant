import React, { useEffect, useState } from 'react'
import type { Settings } from '../types'
import { useSettings } from '../hooks/useSettings'

interface SettingsPanelProps {
  onClose: () => void
}

const DEFAULT_SETTINGS: Settings = {
  llm_provider: 'ollama',
  ollama: { base_url: 'http://localhost:11434', model: 'llama3.1' },
  azure_openai: { endpoint: '', api_key: '', deployment: '', api_version: '2024-02-01' },
}

export function SettingsPanel({ onClose }: SettingsPanelProps) {
  const { settings, providerStatus, loading, error, saveSettings, checkProviderStatus } = useSettings()
  const [form, setForm] = useState<Settings>(DEFAULT_SETTINGS)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (settings) setForm(settings)
  }, [settings])

  const handleSave = async () => {
    await saveSettings(form)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const handleTestConnection = async () => {
    await checkProviderStatus()
  }

  const statusDot = (available: boolean | undefined) =>
    available === undefined ? null : (
      <span className={`w-2 h-2 rounded-full inline-block ml-2 ${available ? 'bg-green-400' : 'bg-red-500'}`} />
    )

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg bg-neutral-900 border border-neutral-700 rounded-2xl shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-800">
          <h2 className="text-base font-semibold text-neutral-100">Settings</h2>
          <button
            onClick={onClose}
            aria-label="Close settings"
            className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-neutral-800 text-neutral-400 hover:text-neutral-200 cursor-pointer transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
              <path fillRule="evenodd" d="M5.47 5.47a.75.75 0 011.06 0L12 10.94l5.47-5.47a.75.75 0 111.06 1.06L13.06 12l5.47 5.47a.75.75 0 11-1.06 1.06L12 13.06l-5.47 5.47a.75.75 0 01-1.06-1.06L10.94 12 5.47 6.53a.75.75 0 010-1.06z" clipRule="evenodd" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-5 max-h-[70vh] overflow-y-auto">
          {/* Provider Selector */}
          <div>
            <label className="block text-xs font-medium text-neutral-400 mb-2 uppercase tracking-wider">
              LLM Provider
            </label>
            <div className="grid grid-cols-2 gap-2">
              {(['ollama', 'azure_openai'] as const).map(p => (
                <button
                  key={p}
                  onClick={() => setForm(prev => ({ ...prev, llm_provider: p }))}
                  className={`px-4 py-2.5 rounded-xl text-sm font-medium cursor-pointer transition-all duration-150 border
                    ${form.llm_provider === p
                      ? 'bg-teal-700/30 border-teal-600 text-teal-300'
                      : 'bg-neutral-800 border-neutral-700 text-neutral-400 hover:border-neutral-600'
                  }`}
                >
                  {p === 'ollama' ? '🦙 Ollama' : '☁️ Azure OpenAI'}
                  {providerStatus && statusDot(
                    p === 'ollama' ? providerStatus.ollama.available : providerStatus.azure_openai.available
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Ollama Settings */}
          {form.llm_provider === 'ollama' && (
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-neutral-400 mb-1.5" htmlFor="ollama-base-url">
                  Base URL
                </label>
                <input
                  id="ollama-base-url"
                  type="text"
                  value={form.ollama.base_url}
                  onChange={e => setForm(prev => ({ ...prev, ollama: { ...prev.ollama, base_url: e.target.value } }))}
                  className="w-full px-3 py-2.5 bg-neutral-800 border border-neutral-700 rounded-xl text-sm text-neutral-100
                    placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-teal-500/50 focus:border-teal-600 transition-all"
                  placeholder="http://localhost:11434"
                />
              </div>
              <div>
                <label className="block text-xs text-neutral-400 mb-1.5" htmlFor="ollama-model">
                  Model
                </label>
                <input
                  id="ollama-model"
                  type="text"
                  value={form.ollama.model}
                  onChange={e => setForm(prev => ({ ...prev, ollama: { ...prev.ollama, model: e.target.value } }))}
                  className="w-full px-3 py-2.5 bg-neutral-800 border border-neutral-700 rounded-xl text-sm text-neutral-100
                    placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-teal-500/50 focus:border-teal-600 transition-all"
                  placeholder="llama3.1"
                />
              </div>
            </div>
          )}

          {/* Azure OpenAI Settings */}
          {form.llm_provider === 'azure_openai' && (
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-neutral-400 mb-1.5" htmlFor="azure-endpoint">
                  Endpoint
                </label>
                <input
                  id="azure-endpoint"
                  type="text"
                  value={form.azure_openai.endpoint}
                  onChange={e => setForm(prev => ({ ...prev, azure_openai: { ...prev.azure_openai, endpoint: e.target.value } }))}
                  className="w-full px-3 py-2.5 bg-neutral-800 border border-neutral-700 rounded-xl text-sm text-neutral-100
                    placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-teal-500/50 focus:border-teal-600 transition-all"
                  placeholder="https://myaccount.openai.azure.com/"
                />
              </div>
              <div>
                <label className="block text-xs text-neutral-400 mb-1.5" htmlFor="azure-api-key">
                  API Key
                </label>
                <input
                  id="azure-api-key"
                  type="password"
                  value={form.azure_openai.api_key}
                  onChange={e => setForm(prev => ({ ...prev, azure_openai: { ...prev.azure_openai, api_key: e.target.value } }))}
                  className="w-full px-3 py-2.5 bg-neutral-800 border border-neutral-700 rounded-xl text-sm text-neutral-100
                    placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-teal-500/50 focus:border-teal-600 transition-all"
                  placeholder="••••••••"
                />
              </div>
              <div>
                <label className="block text-xs text-neutral-400 mb-1.5" htmlFor="azure-deployment">
                  Deployment
                </label>
                <input
                  id="azure-deployment"
                  type="text"
                  value={form.azure_openai.deployment}
                  onChange={e => setForm(prev => ({ ...prev, azure_openai: { ...prev.azure_openai, deployment: e.target.value } }))}
                  className="w-full px-3 py-2.5 bg-neutral-800 border border-neutral-700 rounded-xl text-sm text-neutral-100
                    placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-teal-500/50 focus:border-teal-600 transition-all"
                  placeholder="gpt-4o"
                />
              </div>
              <div>
                <label className="block text-xs text-neutral-400 mb-1.5" htmlFor="azure-api-version">
                  API Version
                </label>
                <input
                  id="azure-api-version"
                  type="text"
                  value={form.azure_openai.api_version}
                  onChange={e => setForm(prev => ({ ...prev, azure_openai: { ...prev.azure_openai, api_version: e.target.value } }))}
                  className="w-full px-3 py-2.5 bg-neutral-800 border border-neutral-700 rounded-xl text-sm text-neutral-100
                    placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-teal-500/50 focus:border-teal-600 transition-all"
                  placeholder="2024-02-01"
                />
              </div>
            </div>
          )}

          {error && (
            <div className="px-3 py-2 bg-red-900/30 border border-red-700/30 rounded-xl text-red-400 text-xs">
              {error}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-neutral-800 gap-3">
          <button
            onClick={handleTestConnection}
            disabled={loading}
            className="px-4 py-2 rounded-xl text-sm bg-neutral-800 hover:bg-neutral-700 text-neutral-300 
              cursor-pointer transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Test Connection
          </button>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-sm text-neutral-400 hover:text-neutral-200 cursor-pointer transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={loading}
              className="px-5 py-2 rounded-xl text-sm font-medium bg-teal-600 hover:bg-teal-500 text-white
                cursor-pointer transition-all duration-150 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saved ? '✓ Saved' : loading ? 'Saving…' : 'Save'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
