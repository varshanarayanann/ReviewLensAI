import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useParams } from 'react-router'
import { AppShell } from '../components/layout/AppShell'
import { Alert } from '../components/ui/Alert'
import { AnalysisTargetWorkspaceView, type AnalysisTargetWorkspaceState } from '../components/workspace/AnalysisTargetWorkspaceView'
import { ApiError, getWorkspace, uploadReviews, type IngestionResultResponse } from '../lib/api/client'
import { useAuth } from '../lib/auth/AuthContext'
import { MESSAGES } from '../lib/messages'

function Workspace({ apiBaseUrl, targetId, token }: { apiBaseUrl: string; targetId: string; token: string }) {
  const { expireSession } = useAuth()
  const [state, setState] = useState<AnalysisTargetWorkspaceState>({ kind: 'loading' })
  const [result, setResult] = useState<IngestionResultResponse | null>(null)
  const [attempt, setAttempt] = useState(0)
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const mounted = useRef(false)
  const uploading = useRef(false)
  const fileInput = useRef<HTMLInputElement>(null)

  function handleFailure(failure: unknown, submission = false) {
    if (failure instanceof ApiError && failure.status === 401) {
      // AuthProvider clears local state even if remote sign-out fails.
      void expireSession().catch(() => {})
    } else if (failure instanceof ApiError && [403, 404].includes(failure.status)) {
      setState({ kind: 'missing' })
    } else {
      const message = failure instanceof ApiError
        ? (failure.status === 422 && submission ? MESSAGES.csvFormat : MESSAGES.unexpected)
        : MESSAGES.offline
      if (submission) setError(message)
      else setState({ kind: 'error', message })
    }
  }

  useEffect(() => {
    let active = true
    mounted.current = true
    getWorkspace(apiBaseUrl, targetId, token)
      .then(({ target, result: latest }) => {
        if (!active) return
        setResult(latest)
        setState({ kind: 'ready', target: {
          name: target.name, platform: target.platform === 'google_maps' ? 'Google Maps' : target.platform,
          sourceReference: target.source_url, latestIngestionState: latest?.state,
        } })
      })
      .catch((failure: unknown) => {
        if (!active) return
        if (failure instanceof ApiError && failure.status === 401) {
          void expireSession().catch(() => {})
        } else if (failure instanceof ApiError && [403, 404].includes(failure.status)) {
          setState({ kind: 'missing' })
        } else {
          setState({ kind: 'error', message: failure instanceof ApiError ? MESSAGES.unexpected : MESSAGES.offline })
        }
      })
    return () => { active = false; mounted.current = false }
  }, [apiBaseUrl, targetId, token, expireSession, attempt])

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (uploading.current || state.kind !== 'ready' || result?.state === 'processing') return
    if (!file || !file.name.toLowerCase().endsWith('.csv') || file.size > 1_000_000) {
      setError(MESSAGES.csvFile)
      fileInput.current?.focus()
      return
    }
    uploading.current = true
    setBusy(true)
    setError('')
    try {
      const csv = await file.text()
      if (!mounted.current) return
      const next = await uploadReviews(apiBaseUrl, targetId, token, csv)
      if (!mounted.current) return
      setResult(next)
      setState({ kind: 'ready', target: { ...state.target, latestIngestionState: next.state } })
    } catch (failure) {
      if (mounted.current) handleFailure(failure, true)
    } finally {
      uploading.current = false
      if (mounted.current) setBusy(false)
    }
  }

  function refresh() {
    setState({ kind: 'loading' })
    setResult(null)
    setFile(null)
    setError('')
    setAttempt((value) => value + 1)
  }

  return <>
    <AnalysisTargetWorkspaceView state={state}>
      <section className="workspace-ingestion" aria-live="polite">
        <h2>Ingest reviews</h2>
        <p className="muted">{MESSAGES.ingestionUnavailable}</p>
        {result && <Alert variant={
          result.state === 'failed' ? 'danger'
            : result.state === 'partial' ? 'warning'
              : result.state === 'processing' ? 'info' : 'success'
        }>{result.message}</Alert>}
        <h3>Upload a CSV</h3>
        <p id="csv-help" className="muted">{MESSAGES.csvRecovery}</p>
        <form className="form" onSubmit={submit} noValidate>
          <label htmlFor="reviews-csv">Reviews CSV file *</label>
          <input ref={fileInput} id="reviews-csv" type="file" accept=".csv" required
            aria-invalid={!!error} aria-describedby={`csv-help${error ? ' csv-error' : ''}`}
            disabled={busy || result?.state === 'processing'}
            onChange={(event) => { setFile(event.target.files?.[0] ?? null); setError('') }} />
          {error && <div id="csv-error"><Alert variant="danger">{error}</Alert></div>}
          <button className="button button--primary" disabled={busy || result?.state === 'processing'}>
            {busy ? 'Uploading...' : 'Upload reviews'}
          </button>
          {result?.state === 'processing' && <p>{MESSAGES.ingestionBusy}</p>}
        </form>
      </section>
    </AnalysisTargetWorkspaceView>
    {state.kind !== 'loading' && state.kind !== 'missing' && state.kind !== 'forbidden' && <button
      className="button button--secondary workspace-refresh" disabled={busy} onClick={refresh}>Refresh workspace</button>}
  </>
}

export default function AnalysisTargetWorkspacePage({ apiBaseUrl }: { apiBaseUrl: string }) {
  const { targetId = '' } = useParams()
  const { session } = useAuth()
  return <AppShell>{session && <Workspace
    key={`${apiBaseUrl}:${targetId}:${session.user.id}:${session.access_token}`}
    apiBaseUrl={apiBaseUrl} targetId={targetId} token={session.access_token} />}</AppShell>
}
