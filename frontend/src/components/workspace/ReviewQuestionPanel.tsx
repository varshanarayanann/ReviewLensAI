import { useEffect, useRef, useState, type FormEvent } from 'react'
import { ApiError, askReviewQuestion, type ReviewAnswerResponse } from '../../lib/api/client'
import { useAuth } from '../../lib/auth/AuthContext'
import { MESSAGES } from '../../lib/messages'
import { Alert } from '../ui/Alert'

const MAX_QUESTION_LENGTH = 1000
const answerTitles = {
  answered: 'ReviewLens response',
  insufficient_evidence: 'Not enough evidence',
  out_of_scope: 'Outside review scope',
}

interface ReviewQuestionPanelProps {
  apiBaseUrl: string
  targetId: string
  targetName: string
  token: string
  onAccessDenied: () => void
}

export function ReviewQuestionPanel({ apiBaseUrl, targetId, targetName, token, onAccessDenied }: ReviewQuestionPanelProps) {
  const { expireSession } = useAuth()
  const [question, setQuestion] = useState('')
  const [fieldError, setFieldError] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [answer, setAnswer] = useState<ReviewAnswerResponse | null>(null)
  const input = useRef<HTMLTextAreaElement>(null)
  const request = useRef<AbortController | null>(null)

  useEffect(() => () => request.current?.abort(), [])

  if (answer?.status === 'no_reviews') {
    return <p aria-live="polite" className="muted">{MESSAGES.questionNoReviews}</p>
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (request.current) return

    const text = question.trim()
    const validationError = !text ? MESSAGES.questionRequired
      : Array.from(text).length > MAX_QUESTION_LENGTH ? MESSAGES.questionTooLong : ''
    setFieldError(validationError)
    if (validationError) {
      input.current?.focus()
      return
    }

    const controller = new AbortController()
    request.current = controller
    setBusy(true)
    setError('')
    setAnswer(null)
    try {
      const response = await askReviewQuestion(apiBaseUrl, targetId, token, text, controller.signal)
      if (controller.signal.aborted) return
      if (response.target_id !== targetId) {
        setError(MESSAGES.questionUnavailable)
        return
      }
      setAnswer(response)
    } catch (failure) {
      if (controller.signal.aborted) return
      if (failure instanceof ApiError) {
        if (failure.status === 401) void expireSession().catch(() => {})
        else if (failure.status === 403 || failure.status === 404) onAccessDenied()
        else setError(failure.status === 422 ? MESSAGES.questionCannotProcess : MESSAGES.questionUnavailable)
      } else {
        setError(failure instanceof TypeError ? MESSAGES.offline : MESSAGES.questionUnavailable)
      }
    } finally {
      request.current = null
      if (!controller.signal.aborted) setBusy(false)
    }
  }

  return (
    <>
      <form className="form" onSubmit={submit} noValidate>
        <label htmlFor="review-question">Question *</label>
        <p id="review-question-help" className="muted">
          Ask about saved reviews for {targetName}. Use up to {MAX_QUESTION_LENGTH.toLocaleString('en-US')} characters.
        </p>
        <textarea id="review-question" ref={input} rows={3} required readOnly={busy}
          value={question} aria-invalid={!!fieldError}
          aria-describedby={`review-question-help${fieldError ? ' review-question-error' : ''}`}
          onChange={(event) => { setQuestion(event.target.value); setFieldError('') }} />
        {fieldError && <div id="review-question-error"><Alert variant="danger">{fieldError}</Alert></div>}
        <button className="button button--primary" disabled={busy}>
          {busy ? 'Asking...' : 'Ask question'}
        </button>
      </form>
      {error && <Alert variant="danger">{error}</Alert>}
      <div aria-live="polite">
        {busy && <p className="muted">ReviewLens is preparing a response.</p>}
        {answer && <>
          <h3>{answerTitles[answer.status]}</h3>
          <p className="workspace-answer">{answer.answer}</p>
        </>}
      </div>
    </>
  )
}
