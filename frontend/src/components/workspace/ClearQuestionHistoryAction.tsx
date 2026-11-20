import { useEffect, useRef, useState } from 'react'
import { ApiError, clearQuestionHistory } from '../../lib/api/client'
import { useAuth } from '../../lib/auth/AuthContext'
import { MESSAGES } from '../../lib/messages'
import { Alert } from '../ui/Alert'
import { ConfirmDialog } from '../ui/ConfirmDialog'

interface ClearHistoryProps {
  apiBaseUrl: string
  targetId: string
  targetName: string
  token: string
  disabled: boolean
  onAccessDenied: () => void
  onCleared: () => void
  onPendingChange: (pending: boolean) => void
}

export function ClearQuestionHistoryAction({ apiBaseUrl, targetId, targetName, token, disabled, onAccessDenied, onCleared, onPendingChange }: ClearHistoryProps) {
  const { expireSession } = useAuth()
  const [open, setOpen] = useState(false)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const [cleared, setCleared] = useState(false)
  const trigger = useRef<HTMLButtonElement>(null)
  const request = useRef<AbortController | null>(null)

  useEffect(() => () => {
    request.current?.abort()
    onPendingChange(false)
  }, [onPendingChange])

  async function confirm() {
    if (request.current || disabled) return
    const controller = new AbortController()
    request.current = controller
    setPending(true)
    onPendingChange(true)
    setError('')
    try {
      await clearQuestionHistory(apiBaseUrl, targetId, token, controller.signal)
      if (controller.signal.aborted) return
      setOpen(false)
      setCleared(true)
      onCleared()
      trigger.current?.focus()
    } catch (failure) {
      if (controller.signal.aborted) return
      if (failure instanceof ApiError && failure.status === 401) void expireSession().catch(() => {})
      else if (failure instanceof ApiError && [403, 404].includes(failure.status)) onAccessDenied()
      else setError(failure instanceof TypeError ? MESSAGES.offline : MESSAGES.questionHistoryClearFailed)
    } finally {
      request.current = null
      if (!controller.signal.aborted) {
        setPending(false)
        onPendingChange(false)
      }
    }
  }

  return <div className="workspace-clear-history">
    <button ref={trigger} type="button" className="button button--secondary" disabled={disabled || pending}
      onClick={() => { setError(''); setCleared(false); setOpen(true) }}>Clear Q&A history</button>
    {disabled && <p className="muted">{MESSAGES.questionHistoryClearBusy}</p>}
    {cleared && <Alert variant="success">{MESSAGES.questionHistoryCleared}</Alert>}
    <ConfirmDialog open={open} title={`Clear Q&A history for “${targetName}”?`}
      description="This permanently removes saved questions and responses for this analysis. It does not delete the analysis target, source URL, reviews, or ingestion summary. This can't be undone."
      confirmLabel="Clear Q&A history" pendingLabel="Clearing..." pending={pending}
      onConfirm={() => void confirm()} onCancel={() => { setOpen(false); trigger.current?.focus() }}>
      {error && <Alert variant="danger">{error}</Alert>}
    </ConfirmDialog>
  </div>
}
