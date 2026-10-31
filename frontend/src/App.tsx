import { useEffect, useState } from 'react'
import { getHealth } from './lib/api/client'
import type { AppConfig } from './lib/config'

type BackendStatus = 'checking' | 'connected' | 'unreachable'

const STATUS_TEXT: Record<BackendStatus, string> = {
  checking: 'Checking backend connection...',
  connected: 'Backend connected',
  unreachable: "Can't reach the backend. Check that it is running and that VITE_API_BASE_URL is correct.",
}

export default function App({ config }: { config: AppConfig }) {
  const [status, setStatus] = useState<BackendStatus>('checking')

  useEffect(() => {
    let cancelled = false
    getHealth(config.apiBaseUrl)
      .then(() => !cancelled && setStatus('connected'))
      .catch(() => !cancelled && setStatus('unreachable'))
    return () => {
      cancelled = true
    }
  }, [config.apiBaseUrl])

  return (
    <main className="app">
      <h1>ReviewLens AI</h1>
      <p className="muted">Review Intelligence Portal</p>
      <p role="status" className={`status status--${status}`}>
        {STATUS_TEXT[status]}
      </p>
    </main>
  )
}
