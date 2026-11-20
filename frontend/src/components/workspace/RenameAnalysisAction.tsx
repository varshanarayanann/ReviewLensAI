import { useRef, useState, type FormEvent } from 'react'
import { ApiError, notifyTargetsChanged, renameTarget } from '../../lib/api/client'
import { useAuth } from '../../lib/auth/AuthContext'
import { MESSAGES } from '../../lib/messages'
import { Alert } from '../ui/Alert'

interface RenameAnalysisProps {
  apiBaseUrl: string
  targetId: string
  targetName: string
  token: string
  disabled?: boolean
  onRenamed: (name: string) => void
  onAccessDenied: () => void
}

export function RenameAnalysisAction({
  apiBaseUrl, targetId, targetName, token, disabled, onRenamed, onAccessDenied,
}: RenameAnalysisProps) {
  const { expireSession } = useAuth()
  const [open, setOpen] = useState(false)
  const [name, setName] = useState(targetName)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const request = useRef<AbortController | null>(null)

  function begin() {
    setName(targetName)
    setError('')
    setOpen(true)
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    const next = name.trim()
    if (!next || next.length > 120) {
      setError(MESSAGES.targetNameRequired)
      return
    }
    if (request.current || disabled) return
    const controller = new AbortController()
    request.current = controller
    setPending(true)
    setError('')
    try {
      const updated = await renameTarget(apiBaseUrl, targetId, token, next, controller.signal)
      if (!controller.signal.aborted) {
        onRenamed(updated.name)
        notifyTargetsChanged()
        setOpen(false)
      }
    } catch (failure) {
      if (controller.signal.aborted) return
      if (failure instanceof ApiError && failure.status === 401) {
        void expireSession().catch(() => {})
      } else if (failure instanceof ApiError && [403, 404].includes(failure.status)) {
        onAccessDenied()
      } else {
        setError(failure instanceof ApiError
          ? failure.status === 422 ? MESSAGES.targetNameRequired : MESSAGES.targetRenameFailed
          : MESSAGES.offline)
      }
    } finally {
      request.current = null
      if (!controller.signal.aborted) setPending(false)
    }
  }

  if (!open) {
    return <button type="button" className="button button--secondary" disabled={disabled} onClick={begin}>
      Rename analysis
    </button>
  }

  return (
    <form className="form rename-analysis" onSubmit={(event) => void submit(event)}>
      <label htmlFor="analysis-name">Analysis name *
        <input id="analysis-name" required maxLength={120} value={name} disabled={pending}
          onChange={(event) => setName(event.target.value)} />
      </label>
      {error && <Alert variant="danger">{error}</Alert>}
      <div className="rename-analysis__actions">
        <button type="button" className="button button--secondary" disabled={pending}
          onClick={() => setOpen(false)}>Cancel</button>
        <button type="submit" className="button button--primary" disabled={pending || disabled}>
          {pending ? 'Saving…' : 'Save name'}
        </button>
      </div>
    </form>
  )
}
