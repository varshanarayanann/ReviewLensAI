import { stubFetchWithEmptyHistory } from '../test/emptyHistory'
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { Link, MemoryRouter } from 'react-router'
import { beforeEach, expect, it, vi } from 'vitest'
import App from '../App'
import { MESSAGES } from '../lib/messages'
import { createFakeAuth, fakeSession } from '../test/fakeAuth'

const config = { apiBaseUrl: 'http://api.test', supabaseUrl: 'https://auth.test', supabaseAnonKey: 'public' }
const target = { id: 'target-a', name: 'Saved park', platform: 'google_maps', source_url: 'https://google.com/maps/place/Park', created_at: '2026-01-01T12:00:00Z' }
const saved = { id: 'review-a', target_id: target.id, run_id: 'run-a', rating: 5, review_text: 'Persisted walking paths review' }
const summary = { target_id: target.id, review_count: 1, average_rating: 5 }
const run = { run_id: 'run-a', target_id: target.id, state: 'succeeded', persisted_count: 1, rejected_count: 0, message: 'Imported 1 review; rejected 0 records.' }
const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status })
type Fetcher = (url: string, options?: RequestInit) => Promise<Response>
let fetchMock: ReturnType<typeof vi.fn<Fetcher>>

function defaultFetch(url: string) {
  return Promise.resolve(json(url.includes('/reviews?') ? [saved]
    : url.endsWith('/summary') ? summary : url.endsWith('/latest') ? run
      : url.endsWith('/api/targets') ? [target] : target))
}

beforeEach(() => {
  fetchMock = vi.fn(defaultFetch)
  stubFetchWithEmptyHistory(fetchMock)
})

function show(path = '/targets/target-a', fake = createFakeAuth(fakeSession())) {
  return render(<MemoryRouter initialEntries={[path]}>
    <Link to="/targets/target-b">Open another saved analysis</Link>
    <App config={config} authClient={fake.client} />
  </MemoryRouter>)
}

async function openReviews() {
  fireEvent.click(await screen.findByRole('button', { name: 'View saved reviews' }))
  return screen.findByRole('list', { name: 'Saved reviews' })
}

it('reopens from the dashboard after a new session and restores server data without re-ingestion', async () => {
  const first = show()
  await openReviews()
  expect(await screen.findByText(saved.review_text)).toBeInTheDocument()
  first.unmount()
  const session = { ...fakeSession(), access_token: 'new-session-token' }
  fetchMock.mockClear()
  show('/dashboard', createFakeAuth(session))
  fireEvent.click(await screen.findByRole('link', { name: 'Open Saved park' }))
  expect(await screen.findByRole('heading', { name: target.name })).toBeInTheDocument()
  expect(screen.getByRole('link', { name: target.source_url })).toHaveAttribute('href', target.source_url)
  expect(screen.getByText('Ingested')).toBeInTheDocument()
  expect(await screen.findByText('5.0 / 5')).toBeInTheDocument()
  expect(screen.getByText(run.message)).toBeInTheDocument()
  await openReviews()
  expect(await screen.findByText(saved.review_text)).toBeInTheDocument()
  expect(fetchMock.mock.calls.every(([, options]) => options?.headers &&
    (options.headers as Record<string, string>).Authorization === 'Bearer new-session-token')).toBe(true)
  expect(fetchMock.mock.calls.some(([url, options]) => url.includes('/questions') || options?.method === 'POST')).toBe(false)
})

it('keeps the deep link through login and opens the saved workspace', async () => {
  const fake = createFakeAuth()
  fake.auth.signInWithPassword.mockResolvedValue({ data: { session: fakeSession() }, error: null })
  show('/targets/target-a', fake)
  expect(await screen.findByRole('heading', { name: 'Log in' })).toBeInTheDocument()
  expect(fetchMock).not.toHaveBeenCalled()
  fireEvent.change(screen.getByLabelText('Email *'), { target: { value: 'user.a@example.com' } })
  fireEvent.change(screen.getByLabelText('Password *'), { target: { value: 'password123' } })
  fireEvent.click(screen.getByRole('button', { name: 'Log in' }))
  expect(await screen.findByRole('heading', { name: target.name })).toBeInTheDocument()
  expect(await screen.findByText('5.0 / 5')).toBeInTheDocument()
})

it('keeps previously persisted reviews available after a failed latest ingestion', async () => {
  fetchMock.mockImplementation((url) => url.endsWith('/latest')
    ? Promise.resolve(json({ ...run, state: 'failed', message: 'Collection failed.', persisted_count: 0 })) : defaultFetch(url))
  show()
  expect(await screen.findByText('Failed')).toBeInTheDocument()
  await openReviews()
  expect(await screen.findByText(saved.review_text)).toBeInTheDocument()
  expect(screen.getByRole('textbox', { name: 'Question *' })).toBeEnabled()
})

it('shows an explicit empty dataset for a saved target without reviews', async () => {
  fetchMock.mockImplementation((url) => url.endsWith('/summary')
    ? Promise.resolve(json({ ...summary, review_count: 0, average_rating: null })) : defaultFetch(url))
  show()
  expect(await screen.findByText(MESSAGES.savedReviewsEmpty)).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'View saved reviews' })).not.toBeInTheDocument()
})

it('paginates persisted reviews and renders rating-only text safely', async () => {
  const reviews = Array.from({ length: 20 }, (_, index) => ({ ...saved, id: `review-${index}`, review_text: `Review ${index}` }))
  fetchMock.mockImplementation((url) => url.endsWith('/summary') ? Promise.resolve(json({ ...summary, review_count: 21 }))
    : url.includes('/reviews?') ? Promise.resolve(json(url.endsWith('offset=0') ? reviews : [{ ...saved, id: 'last', review_text: '' }])) : defaultFetch(url))
  show()
  const list = await openReviews()
  expect(within(list).getAllByRole('listitem')).toHaveLength(20)
  fireEvent.click(screen.getByRole('button', { name: 'Next reviews' }))
  expect(await screen.findByText(MESSAGES.ratingOnlyReview)).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Next reviews' })).toBeDisabled()
  fireEvent.click(screen.getByRole('button', { name: 'Previous reviews' }))
  expect(await screen.findByText('Review 0')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Previous reviews' })).toBeDisabled()
})

it.each([[503, MESSAGES.savedReviewsUnavailable], [0, MESSAGES.offline]])('supports safe retry after a review request fails (%s)', async (status, message) => {
  fetchMock.mockImplementation((url) => url.includes('/reviews?')
    ? status ? Promise.resolve(json({ detail: 'private error' }, status)) : Promise.reject(new Error('private error')) : defaultFetch(url))
  show()
  fireEvent.click(await screen.findByRole('button', { name: 'View saved reviews' }))
  expect(await screen.findByRole('alert')).toHaveTextContent(message)
  fetchMock.mockImplementation(defaultFetch)
  fireEvent.click(screen.getByRole('button', { name: 'Retry saved reviews' }))
  expect(await screen.findByText(saved.review_text)).toBeInTheDocument()
})

it.each([[401, 'Log in'], [404, 'Analysis target not found']])('handles review authorization failures (%s)', async (status, heading) => {
  fetchMock.mockImplementation((url) => url.includes('/reviews?') ? Promise.resolve(json({}, status)) : defaultFetch(url))
  show()
  fireEvent.click(await screen.findByRole('button', { name: 'View saved reviews' }))
  expect(await screen.findByRole('heading', { name: heading })).toBeInTheDocument()
  expect(screen.queryByText(saved.review_text)).not.toBeInTheDocument()
})

it('ignores an old target review request after switching analyses', async () => {
  let complete!: (value: Response) => void
  const pending = new Promise<Response>((resolve) => { complete = resolve })
  fetchMock.mockImplementation((url) => url.includes('target-b')
    ? Promise.resolve(json(url.endsWith('/latest') ? null : url.endsWith('/summary') ? { ...summary, target_id: 'target-b' }
      : url.includes('/reviews?') ? [{ ...saved, target_id: 'target-b', review_text: 'B customer service' }] : { ...target, id: 'target-b', name: 'Another saved business' }))
    : url.includes('/reviews?') ? pending : defaultFetch(url))
  show()
  fireEvent.click(await screen.findByRole('button', { name: 'View saved reviews' }))
  expect(await screen.findByText('Loading saved reviews…')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('link', { name: 'Open another saved analysis' }))
  expect(await screen.findByRole('heading', { name: 'Another saved business' })).toBeInTheDocument()
  await openReviews()
  await act(async () => complete(json([saved])))
  expect(screen.getByText('B customer service')).toBeInTheDocument()
  expect(screen.queryByText(saved.review_text)).not.toBeInTheDocument()
})

it('renders review text as text, supports expansion, and aborts when hidden', async () => {
  const raw = '<script>untrusted()</script>' + 'long text '.repeat(40)
  fetchMock.mockImplementation((url) => url.includes('/reviews?') ? Promise.resolve(json([{ ...saved, review_text: raw }])) : defaultFetch(url))
  show()
  await openReviews()
  expect(document.querySelector('.saved-review-text')?.textContent).toBe(raw)
  expect(document.querySelector('.saved-review-item script')).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: 'Show more' }))
  expect(screen.getByRole('button', { name: 'Show less' })).toHaveAttribute('aria-expanded', 'true')
  fireEvent.click(screen.getByRole('button', { name: 'Show less' }))
  fireEvent.click(screen.getByRole('button', { name: 'Hide saved reviews' }))
  await waitFor(() => expect(screen.queryByRole('list', { name: 'Saved reviews' })).not.toBeInTheDocument())
  const request = fetchMock.mock.calls.find(([url]) => url.includes('/reviews?'))!
  expect(request[1]?.signal?.aborted).toBe(true)
})
