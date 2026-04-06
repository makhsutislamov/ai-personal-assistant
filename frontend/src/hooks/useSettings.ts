import { useCallback, useEffect, useState } from 'react'
import type { ProviderStatus, Settings } from '../types'
import { getProviderStatus, getSettings, updateSettings } from '../services/api'

interface UseSettingsReturn {
  settings: Settings | null
  providerStatus: ProviderStatus | null
  loading: boolean
  error: string | null
  loadSettings: () => Promise<void>
  saveSettings: (settings: Settings) => Promise<void>
  checkProviderStatus: () => Promise<void>
}

export function useSettings(): UseSettingsReturn {
  const [settings, setSettings] = useState<Settings | null>(null)
  const [providerStatus, setProviderStatus] = useState<ProviderStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadSettings = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getSettings()
      setSettings(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load settings')
    } finally {
      setLoading(false)
    }
  }, [])

  const saveSettings = useCallback(async (newSettings: Settings) => {
    setLoading(true)
    setError(null)
    try {
      const saved = await updateSettings(newSettings)
      setSettings(saved)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save settings')
    } finally {
      setLoading(false)
    }
  }, [])

  const checkProviderStatus = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const status = await getProviderStatus()
      setProviderStatus(status)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to check provider status')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadSettings()
  }, [loadSettings])

  return { settings, providerStatus, loading, error, loadSettings, saveSettings, checkProviderStatus }
}
