import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router'
import { ApiError, deleteTarget } from '../../lib/api/client'
import { useAuth } from '../../lib/auth/AuthContext'
import { MESSAGES } from '../../lib/messages'
import { Alert } from '../ui/Alert'
import { ConfirmDialog } from '../ui/ConfirmDialog'

interface DeleteTargetProps {
  apiBaseUrl: string
  targetId: string
  targetName: string
  token: string
  disabled: boolean
  onAccessDenied: () => void
}

export function DeleteTargetAction({ apiBaseUrl, targetId, targetName, token, disabled, onAccessDenied }: DeleteTargetProps) {
  const navigate = useNavigate()
  const { expireSession } = useAuth()
  const [open, setOpen] = useState(false)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const trigger = useRef<HTMLButtonElement>(null)
  const request = useRef<AbortController | null>(null)

  useEffect(() => () => request.current?.abort(), [])

  async function confirm() {
    if (request.current || disabled) return
    const controller = new AbortController()
    request.current = controller
    setPending(true)
    setError('')
    try {
      await deleteTarget(apiBaseUrl, targetId, token, controller.signal)
      if (!controller.signal.aborted) void navigate('/dashboard', { replace: true })
    } catch (failure) {
      if (controller.signal.aborted) return
      if (failure instanceof ApiError && failure.status === 401) {
        void expireSession().catch(() => {})
      } else if (failure instanceof ApiError && [403, 404].includes(failure.status)) {
        onAccessDenied()
      } else {
        setError(failure instanceof ApiError
          ? failure.status === 409 ? MESSAGES.targetDeleteBusy : MESSAGES.targetDeleteFailed
          : MESSAGES.offline)
      }
    } finally {
      request.current = null
      if (!controller.signal.aborted) setPending(false)
    }
  }

  return <>
    <details className="workspace-target-actions">
      <summary>Target actions</summary>
      <button ref={trigger} type="button" className="button button--secondary" disabled={disabled}
        onClick={() => { setError(''); setOpen(true) }}>Delete target</button>
      {disabled && <p className="muted">{MESSAGES.targetDeleteBusy}</p>}
    </details>
    <ConfirmDialog open={open} title={`Delete “${targetName}”?`}
      description="This permanently removes the target, all its reviews, and its ingestion history. This can't be undone."
      confirmLabel="Delete target" pending={pending} onConfirm={() => void confirm()}
      onCancel={() => { setOpen(false); trigger.current?.focus() }}>
      {error && <Alert variant="danger">{error}</Alert>}
    </ConfirmDialog>
  </>
}
