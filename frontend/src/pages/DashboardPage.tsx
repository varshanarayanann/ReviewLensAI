import { Link } from 'react-router'
import { useEffect, useState } from 'react'
import { AppShell } from '../components/layout/AppShell'
import { Alert } from '../components/ui/Alert'
import { EmptyState } from '../components/ui/EmptyState'
import { PageHeader } from '../components/ui/PageHeader'
import { Skeleton } from '../components/ui/Skeleton'
import { TargetCard } from '../components/ui/TargetCard'
import { ApiError, getTargets, type AnalysisTargetResponse } from '../lib/api/client'
import { useAuth } from '../lib/auth/AuthContext'
import { MESSAGES } from '../lib/messages'

type LoadState =
  | { kind: 'loading' }
  | { kind: 'ready'; targets: AnalysisTargetResponse[] }
  | { kind: 'error'; message: string }

function TargetList({ apiBaseUrl, accessToken }: { apiBaseUrl: string; accessToken: string }) {
  const { expireSession } = useAuth()
  const [state, setState] = useState<LoadState>({ kind: 'loading' })
  const [attempt, setAttempt] = useState(0)
  const [showSkeleton, setShowSkeleton] = useState(false)

  useEffect(() => {
    let active = true
    const timer = setTimeout(() => { if (active) setShowSkeleton(true) }, 300)
    getTargets(apiBaseUrl, accessToken)
      .then((targets) => { if (active) setState({ kind: 'ready', targets }) })
      .catch((error: unknown) => {
        if (!active) return
        if (error instanceof ApiError && error.status === 401) {
          void expireSession().catch(() => {})
          return
        }
        setState({ kind: 'error', message: error instanceof ApiError ? MESSAGES.unexpected : MESSAGES.offline })
      })
    return () => {
      active = false
      clearTimeout(timer)
    }
  }, [apiBaseUrl, accessToken, expireSession, attempt])

  return (
    <div aria-live="polite">
      {state.kind === 'loading' && <div aria-busy="true" aria-label="Loading analysis targets" className="target-grid">
        {showSkeleton && [0, 1, 2].map((index) => <Skeleton key={index} height={180} />)}
      </div>}
      {state.kind === 'ready' && (state.targets.length === 0
        ? <EmptyState title={MESSAGES.noTargets} description={MESSAGES.addTarget} />
        : <ul className="target-grid" aria-label="Analysis targets">
          {state.targets.map((target) => <li key={target.id}><TargetCard target={target} /></li>)}
        </ul>)}
      {state.kind === 'error' && <div className="stack">
        <Alert variant="danger">{state.message}</Alert>
        <button className="button button--secondary" onClick={() => {
          setState({ kind: 'loading' })
          setShowSkeleton(false)
          setAttempt((value) => value + 1)
        }}>Try again</button>
      </div>}
    </div>
  )
}

export default function DashboardPage({ apiBaseUrl }: { apiBaseUrl: string }) {
  const { session } = useAuth()
  return (
    <AppShell>
      <PageHeader title="Dashboard" description="Your analysis targets"
        action={<Link className="button button--primary button-link" to="/targets/new">New target</Link>} />
      {session && <TargetList key={`${apiBaseUrl}:${session.user.id}:${session.access_token}`}
        apiBaseUrl={apiBaseUrl} accessToken={session.access_token} />}
    </AppShell>
  )
}
