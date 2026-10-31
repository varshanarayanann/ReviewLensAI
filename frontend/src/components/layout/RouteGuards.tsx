import { Navigate, Outlet, useLocation } from 'react-router'
import { useAuth } from '../../lib/auth/AuthContext'
import { AppShellSkeleton } from './AppShell'

export interface RedirectState {
  from?: string
  message?: string
}

function safeReturnPath(state: unknown): string {
  const from = (state as RedirectState | null)?.from
  return typeof from === 'string' && from.startsWith('/') && !from.startsWith('//') ? from : '/dashboard'
}

export function ProtectedRoute() {
  const { status, signOutReason } = useAuth()
  const location = useLocation()

  if (status === 'loading') return <AppShellSkeleton />
  if (status === 'unauthenticated') {
    const state: RedirectState = { from: location.pathname + location.search, message: signOutReason }
    return <Navigate to="/login" replace state={state} />
  }
  return <Outlet />
}

export function PublicOnlyRoute() {
  const { status } = useAuth()
  const location = useLocation()

  if (status === 'loading') return <AppShellSkeleton />
  if (status === 'authenticated') return <Navigate to={safeReturnPath(location.state)} replace />
  return <Outlet />
}

export function RootRedirect() {
  const { status } = useAuth()

  if (status === 'loading') return <AppShellSkeleton />
  return <Navigate to={status === 'authenticated' ? '/dashboard' : '/login'} replace />
}
