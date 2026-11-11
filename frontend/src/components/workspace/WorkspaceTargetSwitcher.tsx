import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { ApiError, getTargets, type AnalysisTargetResponse } from '../../lib/api/client'
import { useAuth } from '../../lib/auth/AuthContext'
import { MESSAGES } from '../../lib/messages'
import { Alert } from '../ui/Alert'

interface TargetSwitcherProps {
  apiBaseUrl: string
  targetId: string
  token: string
}

type TargetsState =
  | { kind: 'loading' }
  | { kind: 'ready'; targets: AnalysisTargetResponse[] }
  | { kind: 'error'; message: string }

function TargetChoices({ apiBaseUrl, targetId, token }: TargetSwitcherProps) {
  const { expireSession } = useAuth()
  const [state, setState] = useState<TargetsState>({ kind: 'loading' })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let active = true
    getTargets(apiBaseUrl, token)
      .then((targets) => {
        if (active) setState({ kind: 'ready', targets })
      })
      .catch((error: unknown) => {
        if (!active) return
        if (error instanceof ApiError && error.status === 401) {
          void expireSession().catch(() => {})
        } else {
          setState({ kind: 'error', message: error instanceof ApiError ? MESSAGES.targetSwitchUnavailable : MESSAGES.offline })
        }
      })
    return () => { active = false }
  }, [apiBaseUrl, token, expireSession, attempt])

  if (state.kind === 'loading') return <p role="status" className="muted">Loading analysis targets…</p>
  if (state.kind === 'error') return <div className="stack">
    <Alert variant="danger">{state.message}</Alert>
    <button type="button" className="button button--secondary" onClick={() => {
      setState({ kind: 'loading' })
      setAttempt((value) => value + 1)
    }}>Retry loading targets</button>
  </div>

  const alternatives = state.targets.filter((target) => target.id !== targetId)
  if (alternatives.length === 0) return <p role="status" className="muted">{MESSAGES.noOtherTargets}</p>

  return <ul className="workspace-target-choices">
    {alternatives.map((target) => <li key={target.id}>
      <Link to={`/targets/${encodeURIComponent(target.id)}`}>
        {target.name}
        <span className="muted">{target.source_url}</span>
      </Link>
    </li>)}
  </ul>
}

export function WorkspaceTargetSwitcher(props: TargetSwitcherProps) {
  const [expanded, setExpanded] = useState(false)

  return <nav className="workspace-target-switcher" aria-label="Switch analysis target">
    <button type="button" className="button button--secondary" aria-expanded={expanded}
      aria-controls="workspace-target-choices" onClick={() => setExpanded((value) => !value)}>
      Switch target
    </button>
    <div id="workspace-target-choices" hidden={!expanded}>
      {expanded && <TargetChoices {...props} />}
    </div>
  </nav>
}
