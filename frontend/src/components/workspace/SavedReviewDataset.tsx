import { useEffect, useState } from 'react'
import { ApiError, getSavedReviews, type PersistedReviewResponse } from '../../lib/api/client'
import { useAuth } from '../../lib/auth/AuthContext'
import { MESSAGES } from '../../lib/messages'
import { Alert } from '../ui/Alert'

interface DatasetProps {
  apiBaseUrl: string
  targetId: string
  token: string
  total: number
  onAccessDenied: () => void
}

function ReviewItem({ review }: { review: PersistedReviewResponse }) {
  const [expanded, setExpanded] = useState(false)
  const long = review.review_text.length > 240 || review.review_text.split('\n').length > 4
  return <li className="saved-review-item">
    <p><span className="saved-review-stars" aria-hidden="true">{'★'.repeat(review.rating)}</span> {review.rating} out of 5</p>
    <p className={`saved-review-text${expanded ? '' : ' saved-review-text--clamped'}`}>
      {review.review_text || MESSAGES.ratingOnlyReview}
    </p>
    {long && <button type="button" className="button button--secondary" aria-expanded={expanded}
      onClick={() => setExpanded((value) => !value)}>{expanded ? 'Show less' : 'Show more'}</button>}
  </li>
}

function ReviewPage({ apiBaseUrl, targetId, token, total, onAccessDenied }: DatasetProps) {
  const { expireSession } = useAuth()
  const [offset, setOffset] = useState(0)
  const [attempt, setAttempt] = useState(0)
  const [state, setState] = useState<
    { kind: 'loading' } | { kind: 'error'; message: string } | { kind: 'ready'; reviews: PersistedReviewResponse[] }
  >({ kind: 'loading' })

  useEffect(() => {
    const controller = new AbortController()
    getSavedReviews(apiBaseUrl, targetId, token, offset, controller.signal)
      .then((reviews) => { if (!controller.signal.aborted) setState({ kind: 'ready', reviews }) })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return
        if (error instanceof ApiError && error.status === 401) void expireSession().catch(() => {})
        else if (error instanceof ApiError && [403, 404].includes(error.status)) onAccessDenied()
        else setState({ kind: 'error', message: error instanceof ApiError ? MESSAGES.savedReviewsUnavailable : MESSAGES.offline })
      })
    return () => controller.abort()
  }, [apiBaseUrl, targetId, token, offset, attempt, expireSession, onAccessDenied])

  return <div aria-live="polite" aria-busy={state.kind === 'loading'}>
    {state.kind === 'loading' && <p role="status">Loading saved reviews…</p>}
    {state.kind === 'error' && <>
      <Alert variant="danger">{state.message}</Alert>
      <button type="button" className="button button--secondary" onClick={() => {
        setState({ kind: 'loading' }); setAttempt((value) => value + 1)
      }}>Retry saved reviews</button>
    </>}
    {state.kind === 'ready' && (state.reviews.length === 0
      ? <p>No reviews on this page. Refresh the workspace to reload the current dataset.</p>
      : <>
        <p>Showing reviews {offset + 1}–{offset + state.reviews.length} of {total}</p>
        <ul className="saved-review-list" aria-label="Saved reviews">
          {state.reviews.map((review) => <ReviewItem key={review.id} review={review} />)}
        </ul>
      </>)}
    <div className="saved-review-pagination">
      <button type="button" className="button button--secondary" disabled={offset === 0 || state.kind === 'loading'}
        onClick={() => { setState({ kind: 'loading' }); setOffset((value) => Math.max(0, value - 20)) }}>Previous reviews</button>
      <button type="button" className="button button--secondary"
        disabled={state.kind !== 'ready' || offset + state.reviews.length >= total || state.reviews.length === 0}
        onClick={() => { setState({ kind: 'loading' }); setOffset((value) => value + 20) }}>Next reviews</button>
    </div>
  </div>
}

export function SavedReviewDataset(props: DatasetProps) {
  const [open, setOpen] = useState(false)
  return <section className="workspace-saved-reviews" aria-labelledby="saved-reviews-title">
    <h2 id="saved-reviews-title">Reviews ({props.total})</h2>
    {props.total === 0 ? <p className="muted">{MESSAGES.savedReviewsEmpty}</p> : <>
      <button type="button" className="button button--secondary" aria-expanded={open}
        onClick={() => setOpen((value) => !value)}>{open ? 'Hide saved reviews' : 'View saved reviews'}</button>
      {open && <ReviewPage {...props} />}
    </>}
  </section>
}
