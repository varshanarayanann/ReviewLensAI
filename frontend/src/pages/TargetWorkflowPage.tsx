import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router'
import { AppShell } from '../components/layout/AppShell'
import { Alert } from '../components/ui/Alert'
import { ApiError, targetRequest } from '../lib/api/client'
import { useAuth } from '../lib/auth/AuthContext'

export default function TargetWorkflowPage({ apiBaseUrl }: { apiBaseUrl: string }) {
  const { session, expireSession } = useAuth()
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [source, setSource] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const target = await targetRequest<{ id: string }>(
        apiBaseUrl, '', session?.access_token ?? '', { name, source_url: source },
      )
      navigate(`/targets/${target.id}`)
    } catch (failure) {
      if (failure instanceof ApiError && failure.status === 401) {
        await expireSession()
      } else {
        setError(failure instanceof ApiError && failure.status === 422
          ? 'Check the target name (1–120 characters) and enter a valid HTTPS Google Maps business URL.'
          : 'The operation could not be completed. Check your access and try again.')
      }
    } finally { setBusy(false) }
  }

  return <AppShell>
    <h1>Create target</h1><p>Google Maps</p>
    {error && <Alert variant="danger">{error}</Alert>}
    <form className="form" onSubmit={submit}>
      <label>Target name *<input required maxLength={120} value={name} onChange={(event) => setName(event.target.value)} /></label>
      <label>Google Maps URL *<input required type="url" value={source} onChange={(event) => setSource(event.target.value)} /></label>
      <button className="button button--primary" disabled={busy}>{busy ? 'Processing...' : 'Create target'}</button>
    </form>
  </AppShell>
}
