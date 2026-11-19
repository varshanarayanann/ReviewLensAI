import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { Link, MemoryRouter } from 'react-router'
import { beforeEach, expect, it, vi } from 'vitest'
import App from '../App'
import type { QuestionExchangeResponse } from '../lib/api/client'
import { MESSAGES } from '../lib/messages'
import { createFakeAuth, fakeSession } from '../test/fakeAuth'

const config = { apiBaseUrl: 'http://api.test', supabaseUrl: 'https://auth.test', supabaseAnonKey: 'public' }
const target = { id: 'battery', name: 'Battery store', platform: 'google_maps', source_url: 'https://google.com/maps/place/Battery' }
const other = { ...target, id: 'service', name: 'Service center' }
const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status })
const exchange = (id: string, targetId = 'battery'): QuestionExchangeResponse => ({
  id, target_id: targetId, question: `${targetId} question ${id}`, answer: `${targetId} reply ${id}`,
  status: 'answered', review_count: 2, created_at: '2026-11-19T12:00:00Z',
})
const first = exchange('first'), second = exchange('second'), service = exchange('service-first', 'service')
type Fetcher = (url: string, options?: RequestInit) => Promise<Response>
let fetchMock: ReturnType<typeof vi.fn<Fetcher>>
let datasets: Record<string, QuestionExchangeResponse[]>

function standardFetch(url: string, options?: RequestInit): Promise<Response> {
  const active = url.includes('/service') ? other : target
  if (url.includes('/questions?')) {
    const offset = Number(new URL(url).searchParams.get('offset'))
    return Promise.resolve(json(datasets[active.id].slice(offset, offset + 50)))
  }
  if (url.endsWith('/questions') && options?.method === 'POST') {
    const question = JSON.parse(options.body as string).question as string
    const saved = { ...exchange('new', active.id), question }
    datasets[active.id].push(saved)
    return Promise.resolve(json({ target_id: active.id, status: saved.status, answer: saved.answer, review_count: 2 }))
  }
  if (url.endsWith('/latest')) return Promise.resolve(json(null))
  if (url.endsWith('/summary')) return Promise.resolve(json({ target_id: active.id, review_count: 2, average_rating: 4 }))
  if (url.endsWith('/api/targets')) return Promise.resolve(json([target, other]))
  return Promise.resolve(json(active))
}

beforeEach(() => {
  datasets = { battery: [first, second], service: [service] }
  fetchMock = vi.fn(standardFetch)
  vi.stubGlobal('fetch', fetchMock)
})

function show(fake = createFakeAuth(fakeSession())) {
  const view = render(<MemoryRouter initialEntries={['/targets/battery']}>
    <Link to="/targets/service">Open service analysis</Link>
    <Link to="/targets/battery">Open battery analysis</Link>
    <App config={config} authClient={fake.client} />
  </MemoryRouter>)
  return { ...view, fake }
}

async function historyList() {
  return screen.findByRole('list', { name: 'Saved Q&A history' })
}

it('restores persisted questions and answers in server order after a fresh session', async () => {
  const initial = show()
  await historyList()
  initial.unmount()
  fetchMock.mockClear()
  show(createFakeAuth({ ...fakeSession(), access_token: 'fresh-session-token' }))
  const list = await historyList()
  expect(within(list).getAllByRole('listitem').map((item) => within(item).getByRole('heading').textContent))
    .toEqual([first.question, second.question])
  expect(within(list).getByText(first.answer!)).toBeInTheDocument()
  expect(list.querySelector('time')).toHaveAttribute('dateTime', first.created_at)
  expect(fetchMock).toHaveBeenCalledWith('http://api.test/api/targets/battery/questions?limit=50&offset=0',
    expect.objectContaining({ method: 'GET', headers: expect.objectContaining({ Authorization: 'Bearer fresh-session-token' }) }))
  expect(fetchMock.mock.calls.some(([, options]) => options?.method === 'POST')).toBe(false)
})

it('replaces history for A → B → A with clearly different target questions', async () => {
  show()
  await historyList()
  fireEvent.click(screen.getByRole('link', { name: 'Open service analysis' }))
  expect(await screen.findByRole('heading', { name: other.name })).toBeInTheDocument()
  const list = await historyList()
  expect(within(list).getByText(service.question)).toBeInTheDocument()
  expect(screen.queryByText(first.question)).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('link', { name: 'Open battery analysis' }))
  expect(within(await historyList()).getByText(first.question)).toBeInTheDocument()
  expect(screen.queryByText(service.question)).not.toBeInTheDocument()
})

it.each(['resolve', 'reject'])('ignores an obsolete history request after switching (%s)', async (outcome) => {
  let complete!: (value: Response) => void
  let fail!: (reason: Error) => void
  const pending = new Promise<Response>((resolve, reject) => { complete = resolve; fail = reject })
  fetchMock.mockImplementation((url, options) => url.includes('/battery/questions?') ? pending : standardFetch(url, options))
  show()
  expect(await screen.findByText('Loading Q&A history…')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('link', { name: 'Open service analysis' }))
  await historyList()
  await act(async () => outcome === 'resolve' ? complete(json([first])) : fail(new TypeError('private transport')))
  expect(screen.getByText(service.question)).toBeInTheDocument()
  expect(screen.queryByText(first.question)).not.toBeInTheDocument()
  expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  expect(fetchMock.mock.calls.find(([url]) => url.includes('/battery/questions?'))![1]?.signal?.aborted).toBe(true)
})

it('removes old history on account change and respects the new ownership denial', async () => {
  const { fake } = show()
  await historyList()
  fetchMock.mockResolvedValue(json({}, 404))
  const next = fakeSession('user.b@example.com')
  next.user.id = 'user-b'
  next.access_token = 'user-b-token'
  act(() => fake.emit('SIGNED_IN', next))
  expect(screen.queryByText(first.question)).not.toBeInTheDocument()
  expect(await screen.findByRole('heading', { name: 'Analysis target not found' })).toBeInTheDocument()
})

it('offers every history page without truncating at the first fifty exchanges', async () => {
  datasets.battery = Array.from({ length: 52 }, (_, index) => exchange(`q-${index}`))
  show()
  expect(within(await historyList()).getAllByRole('listitem')).toHaveLength(50)
  fireEvent.click(screen.getByRole('button', { name: 'Next questions' }))
  const page = await historyList()
  expect(page).toHaveAttribute('start', '51')
  expect(within(page).getAllByRole('listitem')).toHaveLength(2)
  expect(within(page).getByText('battery question q-50')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Next questions' })).toBeDisabled()
  fireEvent.click(screen.getByRole('button', { name: 'Previous questions' }))
  expect(within(await historyList()).getByText('battery question q-0')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Previous questions' })).toBeDisabled()
})

it('shows a clear empty history and a safe terminal page for an exact page boundary', async () => {
  datasets.battery = []
  const view = show()
  expect(await screen.findByText(MESSAGES.questionHistoryEmpty)).toBeInTheDocument()
  view.unmount()
  datasets.battery = Array.from({ length: 50 }, (_, index) => exchange(`q-${index}`))
  show()
  await historyList()
  fireEvent.click(screen.getByRole('button', { name: 'Next questions' }))
  expect(await screen.findByText('No more saved questions.')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Previous questions' })).toBeEnabled()
})

it('restores outcome messages even when the target currently has no reviews', async () => {
  datasets.battery = [
    { ...first, status: 'no_reviews', answer: null, review_count: 0 },
    { ...second, status: 'insufficient_evidence' },
    { ...exchange('outside'), status: 'out_of_scope' },
  ]
  fetchMock.mockImplementation((url, options) => url.endsWith('/summary')
    ? Promise.resolve(json({ target_id: target.id, review_count: 0, average_rating: null })) : standardFetch(url, options))
  show()
  const list = await historyList()
  expect(within(list).getByText(MESSAGES.questionHistoryNoReviews)).toBeInTheDocument()
  expect(within(list).getByText('Not enough evidence')).toBeInTheDocument()
  expect(within(list).getByText('Outside review scope')).toBeInTheDocument()
  expect(screen.queryByRole('textbox', { name: 'Question *' })).not.toBeInTheDocument()
})

it.each([[503, MESSAGES.questionHistoryUnavailable], [0, MESSAGES.offline]])('handles history failure and retry (%s)', async (status, message) => {
  fetchMock.mockImplementation((url, options) => url.includes('/questions?')
    ? status ? Promise.resolve(json({ detail: 'private SQL' }, status)) : Promise.reject(new TypeError('private network')) : standardFetch(url, options))
  show()
  expect(await screen.findByRole('alert')).toHaveTextContent(message)
  expect(screen.queryByText('private SQL')).not.toBeInTheDocument()
  fetchMock.mockImplementation(standardFetch)
  fireEvent.click(screen.getByRole('button', { name: 'Retry Q&A history' }))
  expect(within(await historyList()).getByText(first.question)).toBeInTheDocument()
})

it.each([[401, 'Log in'], [404, 'Analysis target not found']])('handles history authorization failure (%s)', async (status, heading) => {
  fetchMock.mockImplementation((url, options) => url.includes('/questions?') ? Promise.resolve(json({}, status)) : standardFetch(url, options))
  show()
  expect(await screen.findByRole('heading', { name: heading })).toBeInTheDocument()
  expect(screen.queryByText(first.question)).not.toBeInTheDocument()
})

it.each([{}, [service]])('rejects malformed or other-target history without displaying it (%j)', async (payload) => {
  fetchMock.mockImplementation((url, options) => url.includes('/questions?') ? Promise.resolve(json(payload)) : standardFetch(url, options))
  show()
  expect(await screen.findByRole('alert')).toHaveTextContent(MESSAGES.questionHistoryUnavailable)
  expect(screen.queryByText(service.question)).not.toBeInTheDocument()
})

it('refreshes persisted history after a successful question without losing the current response', async () => {
  show()
  await historyList()
  fireEvent.change(await screen.findByRole('textbox', { name: 'Question *' }), { target: { value: 'New battery question' } })
  fireEvent.click(screen.getByRole('button', { name: 'Ask question' }))
  await waitFor(() => expect(within(screen.getByRole('list', { name: 'Saved Q&A history' })).getByText('New battery question')).toBeInTheDocument())
  expect(within(screen.getByRole('list', { name: 'Saved Q&A history' })).getAllByRole('listitem')).toHaveLength(3)
  expect(screen.getByRole('heading', { name: 'ReviewLens response' })).toBeInTheDocument()
})

it('renders persisted question and response text without interpreting HTML', async () => {
  datasets.battery = [{ ...first, question: '<img src=x onerror=alert(1)>', answer: '<script>alert(1)</script>' }]
  show()
  const list = await historyList()
  expect(within(list).getByText('<img src=x onerror=alert(1)>')).toBeInTheDocument()
  expect(within(list).getByText('<script>alert(1)</script>')).toBeInTheDocument()
  expect(list.querySelector('img,script')).toBeNull()
})
