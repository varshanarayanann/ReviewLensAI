import { useEffect, useState } from 'react'
import { ApiError, getQuestionHistory, type QuestionExchangeResponse } from '../../lib/api/client'
import { useAuth } from '../../lib/auth/AuthContext'
import { MESSAGES } from '../../lib/messages'
import { Alert } from '../ui/Alert'

const outcomeLabels = {
  answered: 'Answered', insufficient_evidence: 'Not enough evidence',
  out_of_scope: 'Outside review scope', no_reviews: 'No reviews',
}

interface HistoryProps {
  apiBaseUrl: string
  targetId: string
  targetName: string
  token: string
  onAccessDenied: () => void
}

export function QuestionHistory({ apiBaseUrl, targetId, targetName, token, onAccessDenied }: HistoryProps) {
  const { expireSession } = useAuth()
  const [offset, setOffset] = useState(0)
  const [attempt, setAttempt] = useState(0)
  const [state, setState] = useState<
    { kind: 'loading' } | { kind: 'error'; message: string } | { kind: 'ready'; rows: QuestionExchangeResponse[] }
  >({ kind: 'loading' })

  useEffect(() => {
    const controller = new AbortController()
    getQuestionHistory(apiBaseUrl, targetId, token, offset, controller.signal)
      .then((rows) => {
        if (controller.signal.aborted) return
        // Fail the whole page if it cannot belong to the active workspace.
        if (!Array.isArray(rows) || rows.some((row) => row.target_id !== targetId)) {
          throw new Error('Invalid history response')
        }
        setState({ kind: 'ready', rows })
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return
        if (error instanceof ApiError && error.status === 401) void expireSession().catch(() => {})
        else if (error instanceof ApiError && [403, 404].includes(error.status)) onAccessDenied()
        else setState({ kind: 'error', message: error instanceof TypeError ? MESSAGES.offline : MESSAGES.questionHistoryUnavailable })
      })
    return () => controller.abort()
  }, [apiBaseUrl, targetId, token, offset, attempt, expireSession, onAccessDenied])

  function changePage(next: number) {
    setState({ kind: 'loading' })
    setOffset(next)
  }

  return <section className="workspace-question-history" aria-labelledby="question-history-title">
    <h2 id="question-history-title">Q&A history</h2>
    <p className="muted">Saved questions for {targetName}, oldest first.</p>
    <div aria-live="polite" aria-busy={state.kind === 'loading'}>
      {state.kind === 'loading' && <p role="status">Loading Q&A history…</p>}
      {state.kind === 'error' && <>
        <Alert variant="danger">{state.message}</Alert>
        <button type="button" className="button button--secondary" onClick={() => {
          setState({ kind: 'loading' }); setAttempt((value) => value + 1)
        }}>Retry Q&A history</button>
      </>}
      {state.kind === 'ready' && (state.rows.length === 0
        ? <p>{offset === 0 ? MESSAGES.questionHistoryEmpty : 'No more saved questions.'}</p>
        : <ol className="question-history-list" start={offset + 1} aria-label="Saved Q&A history">
          {state.rows.map((row) => <li key={row.id} className="question-history-item">
            <h3 className="workspace-answer">{row.question}</h3>
            <p className="muted"><time dateTime={row.created_at}>{new Date(row.created_at).toLocaleString(undefined, {
              year: 'numeric', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
            })}</time> · <span>{outcomeLabels[row.status]}</span></p>
            <p className="workspace-answer">{row.answer ?? MESSAGES.questionHistoryNoReviews}</p>
          </li>)}
        </ol>)}
      <div className="saved-review-pagination">
        <button type="button" className="button button--secondary" disabled={offset === 0 || state.kind === 'loading'}
          onClick={() => changePage(Math.max(0, offset - 50))}>Previous questions</button>
        <button type="button" className="button button--secondary" disabled={state.kind !== 'ready' || state.rows.length < 50}
          onClick={() => changePage(offset + 50)}>Next questions</button>
      </div>
    </div>
  </section>
}
