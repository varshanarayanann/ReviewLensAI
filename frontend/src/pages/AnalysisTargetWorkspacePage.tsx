import { useCallback, useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router'
import { AppShell } from '../components/layout/AppShell'
import { Alert } from '../components/ui/Alert'
import { ReviewQuestionPanel } from '../components/workspace/ReviewQuestionPanel'
import { AnalysisTargetWorkspaceView, type AnalysisTargetWorkspaceState, type ReviewSummaryState } from '../components/workspace/AnalysisTargetWorkspaceView'
import { WorkspaceTargetSwitcher } from '../components/workspace/WorkspaceTargetSwitcher'
import { ApiError, collectGoogleMapsReviews, getReviewSummary, getWorkspace, type IngestionResultResponse } from '../lib/api/client'
import { useAuth } from '../lib/auth/AuthContext'
import { MESSAGES } from '../lib/messages'

function Workspace({ apiBaseUrl, targetId, token }: { apiBaseUrl: string; targetId: string; token: string }) {
  const { expireSession } = useAuth()
  const [state, setState] = useState<AnalysisTargetWorkspaceState>({ kind: 'loading' })
  const [summary, setSummary] = useState<ReviewSummaryState>({ kind: 'loading' })
  const [result, setResult] = useState<IngestionResultResponse | null>(null)
  const [attempt, setAttempt] = useState(0)
  const [collecting, setCollecting] = useState(false)
  const [collectionError, setCollectionError] = useState('')
  const mounted = useRef(false)
  const ingesting = useRef(false)
  const summaryRequestId = useRef(0)

  const refreshSummary = useCallback(async () => {
    const requestId = ++summaryRequestId.current
    setSummary({ kind: 'loading' })
    try {
      const next = await getReviewSummary(apiBaseUrl, targetId, token)
      if (!mounted.current || requestId !== summaryRequestId.current) return
      setSummary({ kind: 'ready', summary: next })
    } catch (failure) {
      if (!mounted.current || requestId !== summaryRequestId.current) return
      if (failure instanceof ApiError && failure.status === 401) {
        void expireSession().catch(() => {})
      } else if (failure instanceof ApiError && [403, 404].includes(failure.status)) {
        setState({ kind: 'missing' })
      } else {
        setSummary({
          kind: 'error',
          message: failure instanceof ApiError ? MESSAGES.unexpected : MESSAGES.offline,
        })
      }
    }
  }, [apiBaseUrl, targetId, token, expireSession])

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
        void refreshSummary()
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
    return () => {
      active = false
      mounted.current = false
      summaryRequestId.current += 1
    }
  }, [apiBaseUrl, targetId, token, expireSession, attempt, refreshSummary])

  async function collect() {
    if (ingesting.current || state.kind !== 'ready' || result?.state === 'processing') return
    ingesting.current = true
    setCollecting(true)
    setCollectionError('')
    try {
      const next = await collectGoogleMapsReviews(apiBaseUrl, targetId, token)
      if (!mounted.current) return
      setResult(next)
      setState({ kind: 'ready', target: { ...state.target, latestIngestionState: next.state } })
      if (next.state === 'succeeded' || next.state === 'partial') void refreshSummary()
    } catch (failure) {
      if (!mounted.current) return
      if (failure instanceof ApiError && failure.status === 401) {
        // AuthProvider clears local state even if remote sign-out fails.
        void expireSession().catch(() => {})
      } else if (failure instanceof ApiError && [403, 404].includes(failure.status)) {
        setState({ kind: 'missing' })
      } else {
        setCollectionError(failure instanceof ApiError ? MESSAGES.mapsCollectionFailed : MESSAGES.offline)
      }
    } finally {
      ingesting.current = false
      if (mounted.current) setCollecting(false)
    }
  }

  function refresh() {
    setState({ kind: 'loading' })
    setResult(null)
    setCollectionError('')
    setAttempt((value) => value + 1)
  }

  return <>
    {state.kind === 'ready' && <WorkspaceTargetSwitcher apiBaseUrl={apiBaseUrl} targetId={targetId} token={token} />}
    <AnalysisTargetWorkspaceView state={state} summary={summary} onRetrySummary={() => void refreshSummary()}>
      {state.kind === 'ready' && <section className="workspace-questions" aria-labelledby="review-questions-title">
        <h2 id="review-questions-title">Ask about reviews</h2>
        {summary.kind === 'ready' && summary.summary.review_count > 0
          ? <ReviewQuestionPanel apiBaseUrl={apiBaseUrl} targetId={targetId}
            targetName={state.target.name} token={token} onAccessDenied={() => setState({ kind: 'missing' })} />
          : <p aria-live="polite" className="muted">{
            summary.kind === 'ready' ? MESSAGES.questionNoReviews
              : summary.kind === 'loading' ? MESSAGES.questionCheckingReviews
                : MESSAGES.questionReviewCheckFailed
          }</p>}
      </section>}
      <section className="workspace-ingestion" aria-live="polite">
        <h2>Ingest reviews</h2>
        <p className="muted">{MESSAGES.ingestionSource}</p>
        <button type="button" className="button button--primary" disabled={collecting || result?.state === 'processing'}
          onClick={() => void collect()}>{collecting ? 'Ingesting...' : 'Ingest reviews'}</button>
        {collecting && <p className="muted">{MESSAGES.mapsCollectionBusy}</p>}
        {result?.state === 'processing' && <p>{MESSAGES.ingestionBusy}</p>}
        {collectionError && <Alert variant="danger">{collectionError}</Alert>}
        {result && <Alert variant={
          result.state === 'failed' ? 'danger'
            : result.state === 'partial' ? 'warning'
              : result.state === 'processing' ? 'info' : 'success'
        }>{result.message}</Alert>}
      </section>
    </AnalysisTargetWorkspaceView>
    {state.kind !== 'loading' && state.kind !== 'missing' && state.kind !== 'forbidden' && <button
      className="button button--secondary workspace-refresh" disabled={collecting} onClick={refresh}>Refresh workspace</button>}
  </>
}

export default function AnalysisTargetWorkspacePage({ apiBaseUrl }: { apiBaseUrl: string }) {
  const { targetId = '' } = useParams()
  const { session } = useAuth()
  return <AppShell>{session && <Workspace
    key={`${apiBaseUrl}:${targetId}:${session.user.id}:${session.access_token}`}
    apiBaseUrl={apiBaseUrl} targetId={targetId} token={session.access_token} />}</AppShell>
}
