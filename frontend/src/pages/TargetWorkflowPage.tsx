import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router'
import { AppShell } from '../components/layout/AppShell'
import { Alert } from '../components/ui/Alert'
import { ApiError, targetRequest } from '../lib/api/client'
import { useAuth } from '../lib/auth/AuthContext'
import { MESSAGES } from '../lib/messages'

type Result = { state: 'processing' | 'succeeded' | 'failed'; persisted_count: number; message: string }

export default function TargetWorkflowPage({ apiBaseUrl }: { apiBaseUrl: string }) {
  const { targetId } = useParams()
  const { session, expireSession } = useAuth()
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [source, setSource] = useState('')
  const [target, setTarget] = useState<{ name: string; source_url: string } | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [result, setResult] = useState<Result | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const token = session?.access_token ?? ''

  useEffect(() => {
    let active = true
    setTarget(null)
    setResult(null)
    setError('')
    if (targetId) targetRequest<{ name: string; source_url: string }>(apiBaseUrl, `/${targetId}`, token)
      .then(value => { if (active) setTarget(value) })
      .catch(() => { if (active) setError('Unable to load this target. Check your access and try again.') })
    if (targetId) targetRequest<Result | null>(apiBaseUrl, `/${targetId}/ingestions/latest`, token)
      .then(value => { if (active) setResult(value) })
      .catch(() => { if (active) setError('Unable to load this target. Check your access and try again.') })
    return () => { active = false }
  }, [apiBaseUrl, targetId, token])

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      if (!targetId) {
        const target = await targetRequest<{ id: string }>(apiBaseUrl, '', token, { name, source_url: source })
        navigate(`/targets/${target.id}`)
      } else {
        if (!file || !file.name.toLowerCase().endsWith('.csv') || file.size > 1_000_000) {
          setError('Choose a CSV file smaller than 1 MB.')
          return
        }
        setResult(await targetRequest<Result>(apiBaseUrl, `/${targetId}/ingestions`, token, { csv_text: await file.text() }))
      }
    } catch (failure) {
      if (failure instanceof ApiError && failure.status === 401) {
        await expireSession()
      } else {
        setError(failure instanceof ApiError && failure.status === 422
          ? targetId ? MESSAGES.csvSourceInvalid : 'Check the target name (1–120 characters) and enter a valid HTTPS Google Maps business URL.'
          : 'The operation could not be completed. Check your access and try again.')
      }
    } finally { setBusy(false) }
  }

  return <AppShell>
    <h1>{targetId ? 'Import reviews' : 'Create target'}</h1>
    <p>Google Maps</p>
    {target && <><h2>{target.name}</h2><p><a href={target.source_url} target="_blank" rel="noopener noreferrer">{target.source_url}</a></p></>}
    {error && <Alert variant="danger">{error}</Alert>}
    {result && <Alert variant={result.state === 'failed' ? 'danger' : result.state === 'processing' ? 'info' : 'success'}>{result.message}</Alert>}
    <form className="form" onSubmit={submit}>
      {!targetId ? <>
        <label>Target name *<input required maxLength={120} value={name} onChange={e => setName(e.target.value)} /></label>
        <label>Google Maps URL *<input required type="url" value={source} onChange={e => setSource(e.target.value)} /></label>
      </> : <>
        <p>CSV recovery import. Include rating and review_text columns. Ratings must be integers from 1 to 5. Maximum 1,000 reviews. Invalid rows reject the entire import; existing reviews are retained.</p>
        <label>CSV file *<input required type="file" accept=".csv" onChange={e => setFile(e.target.files?.[0] ?? null)} /></label>
      </>}
      <button className="button button--primary" disabled={busy || (!!targetId && !target)}>{busy ? 'Processing...' : targetId ? 'Upload reviews' : 'Create target'}</button>
    </form>
  </AppShell>
}
