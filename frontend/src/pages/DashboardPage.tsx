import { useEffect, useState } from 'react'
import { AppShell } from '../components/layout/AppShell'
import { Alert } from '../components/ui/Alert'
import { Skeleton } from '../components/ui/Skeleton'
import { ApiError, getCurrentUser, type CurrentUserResponse } from '../lib/api/client'
import { useAuth } from '../lib/auth/AuthContext'
import { MESSAGES } from '../lib/messages'

type LoadState =
  | { kind: 'loading' }
  | { kind: 'ready'; user: CurrentUserResponse }
  | { kind: 'error'; message: string }

export default function DashboardPage({ apiBaseUrl }: { apiBaseUrl: string }) {
  const { session, expireSession } = useAuth()
  const accessToken = session?.access_token
  const [state, setState] = useState<LoadState>({ kind: 'loading' })

  useEffect(() => {
    if (!accessToken) return
    let cancelled = false
    getCurrentUser(apiBaseUrl, accessToken)
      .then((user) => !cancelled && setState({ kind: 'ready', user }))
      .catch((error: unknown) => {
        if (cancelled) return
        if (error instanceof ApiError && error.status === 401) {
          void expireSession()
          return
        }
        setState({
          kind: 'error',
          message: error instanceof ApiError ? MESSAGES.unexpected : MESSAGES.offline,
        })
      })
    return () => {
      cancelled = true
    }
  }, [apiBaseUrl, accessToken, expireSession])

  return (
    <AppShell>
      <h1>Dashboard</h1>
      <p className="muted">Your analysis targets will appear here.</p>
      <div className="stack">
        {state.kind === 'loading' && <Skeleton width={280} height={20} />}
        {state.kind === 'ready' && <p>Logged in as {state.user.email ?? state.user.id}</p>}
        {state.kind === 'error' && <Alert variant="danger">{state.message}</Alert>}
      </div>
    </AppShell>
  )
}
