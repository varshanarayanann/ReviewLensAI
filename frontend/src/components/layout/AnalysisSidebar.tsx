import { useEffect, useState } from 'react'
import { Link, NavLink, useLocation } from 'react-router'
import { ApiError, getTargets, type AnalysisTargetResponse } from '../../lib/api/client'
import { useAuth } from '../../lib/auth/AuthContext'
import { MESSAGES } from '../../lib/messages'

type LoadState =
  | { kind: 'loading' }
  | { kind: 'ready'; targets: AnalysisTargetResponse[] }
  | { kind: 'error' }

export function AnalysisSidebar({ apiBaseUrl }: { apiBaseUrl: string }) {
  const { session, expireSession } = useAuth()
  const location = useLocation()
  const [state, setState] = useState<LoadState>({ kind: 'loading' })
  const [attempt, setAttempt] = useState(0)
  const activeMatch = location.pathname.match(/^\/targets\/([^/]+)$/)
  const activeId = activeMatch && activeMatch[1] !== 'new' ? activeMatch[1] : null
  const token = session?.access_token

  useEffect(() => {
    if (!token) return
    let active = true
    getTargets(apiBaseUrl, token)
      .then((targets) => { if (active) setState({ kind: 'ready', targets }) })
      .catch((error: unknown) => {
        if (!active) return
        if (error instanceof ApiError && error.status === 401) {
          void expireSession().catch(() => {})
          return
        }
        setState({ kind: 'error' })
      })
    return () => { active = false }
  }, [apiBaseUrl, token, expireSession, attempt, location.pathname])

  useEffect(() => {
    function refresh() { setAttempt((value) => value + 1) }
    window.addEventListener('reviewlens:targets-changed', refresh)
    return () => window.removeEventListener('reviewlens:targets-changed', refresh)
  }, [])

  return (
    <nav className="app-sidebar" aria-label="Analysis navigation">
      <NavLink to="/dashboard" className={({ isActive }) =>
        `app-sidebar__link${isActive ? ' app-sidebar__link--active' : ''}`}>Dashboard</NavLink>
      <Link to="/targets/new" className="button button--secondary button-link app-sidebar__new">
        New target
      </Link>
      <div className="app-sidebar__section">
        <h2 className="app-sidebar__heading">Saved analyses</h2>
        {state.kind === 'loading' && <p className="muted app-sidebar__status">Loading…</p>}
        {state.kind === 'error' && <div className="app-sidebar__status">
          <p className="muted">{MESSAGES.sidebarLoadFailed}</p>
          <button type="button" className="button button--secondary" onClick={() => {
            setState({ kind: 'loading' })
            setAttempt((v) => v + 1)
          }}>
            Try again
          </button>
        </div>}
        {state.kind === 'ready' && state.targets.length === 0
          && <p className="muted app-sidebar__status">{MESSAGES.noSavedAnalyses}</p>}
        {state.kind === 'ready' && state.targets.length > 0 && (
          <ul className="app-sidebar__list">
            {state.targets.map((target) => (
              <li key={target.id}>
                <NavLink
                  to={`/targets/${target.id}`}
                  className={() => `app-sidebar__analysis${activeId === target.id ? ' app-sidebar__analysis--active' : ''}`}
                  title={target.name}
                >
                  <span className="app-sidebar__analysis-name">{target.name}</span>
                  <span className="app-sidebar__badge">Google Maps</span>
                </NavLink>
              </li>
            ))}
          </ul>
        )}
      </div>
    </nav>
  )
}
