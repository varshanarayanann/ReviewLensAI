import { act, fireEvent, render, screen, within } from '@testing-library/react'
import { Link, MemoryRouter } from 'react-router'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import App from '../App'
import { MESSAGES } from '../lib/messages'
import { createFakeAuth, fakeSession } from '../test/fakeAuth'

const config = { apiBaseUrl: 'http://api.test', supabaseUrl: 'https://auth.test', supabaseAnonKey: 'public' }
const target = { id: 'battery', name: 'Battery store', platform: 'google_maps', source_url: 'https://google.com/maps/place/Battery' }
const other = { ...target, id: 'service', name: 'Service center' }
const review = { id: 'review', target_id: target.id, run_id: 'run', review_text: 'Original battery reviews', rating: 5 }
const saved = { id: 'question', target_id: target.id, question: 'Saved battery question', answer: 'Saved battery answer', status: 'answered', review_count: 1, created_at: '2026-11-19T12:00:00Z' }
const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status })
const endpoint = 'http://api.test/api/targets/battery/questions'
type Fetcher = (url: string, options?: RequestInit) => Promise<Response>
let fetchMock: ReturnType<typeof vi.fn<Fetcher>>
let cleared = false

function standardFetch(url: string, options?: RequestInit): Promise<Response> {
  const active = url.includes('/service') ? other : target
  if (url === endpoint && options?.method === 'DELETE') {
    cleared = true
    return Promise.resolve(new Response(null, { status: 204 }))
  }
  if (url.includes('/questions?')) return Promise.resolve(json(cleared && active.id === target.id ? [] : [{ ...saved, target_id: active.id, question: `${active.name} question` }]))
  if (url.endsWith('/questions') && options?.method === 'POST') return Promise.resolve(json({ target_id: active.id, status: 'answered', answer: 'Current response', review_count: 1 }))
  if (url.endsWith('/latest')) return Promise.resolve(json({ target_id: active.id, run_id: 'run', state: 'succeeded', persisted_count: 1, rejected_count: 0, message: 'Imported 1 review; rejected 0 records.' }))
  if (url.endsWith('/summary')) return Promise.resolve(json({ target_id: active.id, review_count: 1, average_rating: 5 }))
  if (url.includes('/reviews?')) return Promise.resolve(json([review]))
  if (url.endsWith('/api/targets')) return Promise.resolve(json([target, other]))
  return Promise.resolve(json(active))
}

beforeEach(() => {
  cleared = false
  Object.defineProperty(HTMLDialogElement.prototype, 'showModal', { configurable: true, value: function (this: HTMLDialogElement) { this.open = true } })
  Object.defineProperty(HTMLDialogElement.prototype, 'close', { configurable: true, value: function (this: HTMLDialogElement) { this.open = false } })
  fetchMock = vi.fn(standardFetch)
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  Reflect.deleteProperty(HTMLDialogElement.prototype, 'showModal')
  Reflect.deleteProperty(HTMLDialogElement.prototype, 'close')
})

function show() {
  render(<MemoryRouter initialEntries={['/targets/battery']}>
    <Link to="/targets/service">Open service analysis</Link>
    <App config={config} authClient={createFakeAuth(fakeSession()).client} />
  </MemoryRouter>)
}

async function confirmDialog() {
  fireEvent.click(await screen.findByRole('button', { name: 'Clear Q&A history' }))
  return screen.getByRole('dialog', { name: 'Clear Q&A history for “Battery store”?' })
}

function deleteCalls() {
  return fetchMock.mock.calls.filter(([, options]) => options?.method === 'DELETE')
}

it('requires named confirmation, focuses Cancel, and does not confuse target deletion', async () => {
  show()
  let dialog = await confirmDialog()
  expect(dialog).toHaveTextContent('does not delete the analysis target, source URL, reviews, or ingestion summary')
  expect(within(dialog).getByRole('button', { name: 'Cancel' })).toHaveFocus()
  expect(deleteCalls()).toHaveLength(0)
  fireEvent.click(within(dialog).getByRole('button', { name: 'Cancel' }))
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Clear Q&A history' })).toHaveFocus()
  dialog = await confirmDialog()
  fireEvent(dialog, new Event('cancel', { bubbles: true, cancelable: true }))
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  const actions = screen.getByText('Target actions').closest('details')!
  actions.open = true
  fireEvent.click(within(actions).getByRole('button', { name: 'Delete target' }))
  expect(screen.getByRole('dialog', { name: 'Delete “Battery store”?' })).toBeInTheDocument()
  expect(deleteCalls()).toHaveLength(0)
})

it('clears saved and current Q&A while preserving the visible target, reviews, source, and ingestion summary', async () => {
  show()
  await screen.findByText('Battery store question')
  fireEvent.click(await screen.findByRole('button', { name: 'View saved reviews' }))
  expect(await screen.findByText(review.review_text)).toBeInTheDocument()
  fireEvent.change(screen.getByRole('textbox', { name: 'Question *' }), { target: { value: 'Current question' } })
  fireEvent.click(screen.getByRole('button', { name: 'Ask question' }))
  expect(await screen.findByText('Current response')).toBeInTheDocument()
  const dialog = await confirmDialog()
  fireEvent.click(within(dialog).getByRole('button', { name: 'Clear Q&A history' }))
  expect(await screen.findByText(MESSAGES.questionHistoryCleared)).toBeInTheDocument()
  expect(await screen.findByText(MESSAGES.questionHistoryEmpty)).toBeInTheDocument()
  expect(screen.queryByText('Current response')).not.toBeInTheDocument()
  expect(screen.queryByText('Battery store question')).not.toBeInTheDocument()
  expect(screen.getByRole('textbox', { name: 'Question *' })).toHaveValue('')
  expect(screen.getByRole('heading', { name: target.name })).toBeInTheDocument()
  expect(screen.getByRole('link', { name: target.source_url })).toHaveAttribute('href', target.source_url)
  expect(screen.getByText('Ingested')).toBeInTheDocument()
  expect(screen.getByText('5.0 / 5')).toBeInTheDocument()
  expect(screen.getByText(review.review_text)).toBeInTheDocument()
  expect(screen.getByText('Imported 1 review; rejected 0 records.')).toBeInTheDocument()
  expect(deleteCalls()).toHaveLength(1)
  expect(deleteCalls()[0][0]).toBe(endpoint)
  expect(deleteCalls()[0][1]?.headers).toEqual({ Authorization: 'Bearer test-access-token' })
  expect(screen.getByRole('button', { name: 'Ask question' })).toBeEnabled()
})

it.each([[503, MESSAGES.questionHistoryClearFailed], [0, MESSAGES.offline]])('preserves history on failure and allows retry (%s)', async (status, message) => {
  fetchMock.mockImplementation((url, options) => options?.method === 'DELETE'
    ? status ? Promise.resolve(json({ detail: 'private SQL' }, status)) : Promise.reject(new TypeError('private transport')) : standardFetch(url, options))
  show()
  await screen.findByText('Battery store question')
  const dialog = await confirmDialog()
  fireEvent.click(within(dialog).getByRole('button', { name: 'Clear Q&A history' }))
  expect(await within(dialog).findByRole('alert')).toHaveTextContent(message)
  expect(screen.getByText('Battery store question')).toBeInTheDocument()
  expect(screen.queryByText('private SQL')).not.toBeInTheDocument()
  fetchMock.mockImplementation(standardFetch)
  fireEvent.click(within(dialog).getByRole('button', { name: 'Clear Q&A history' }))
  expect(await screen.findByText(MESSAGES.questionHistoryEmpty)).toBeInTheDocument()
})

it.each([[401, 'Log in'], [404, 'Analysis target not found']])('handles authorization failures safely (%s)', async (status, heading) => {
  fetchMock.mockImplementation((url, options) => options?.method === 'DELETE' ? Promise.resolve(json({}, status)) : standardFetch(url, options))
  show()
  const dialog = await confirmDialog()
  fireEvent.click(within(dialog).getByRole('button', { name: 'Clear Q&A history' }))
  expect(await screen.findByRole('heading', { name: heading })).toBeInTheDocument()
  expect(screen.queryByText('Battery store question')).not.toBeInTheDocument()
})

it('prevents duplicate clearing, cancellation, and new questions while clearing is pending', async () => {
  let complete!: (value: Response) => void
  const pending = new Promise<Response>((resolve) => { complete = resolve })
  fetchMock.mockImplementation((url, options) => options?.method === 'DELETE' ? pending : standardFetch(url, options))
  show()
  const dialog = await confirmDialog()
  const button = within(dialog).getByRole('button', { name: 'Clear Q&A history' })
  fireEvent.click(button)
  fireEvent.click(button)
  fireEvent(dialog, new Event('cancel', { bubbles: true, cancelable: true }))
  expect(within(dialog).getByRole('button', { name: 'Clearing...' })).toBeDisabled()
  expect(within(dialog).getByRole('button', { name: 'Cancel' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Ask question' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Refresh workspace' })).toBeDisabled()
  expect(deleteCalls()).toHaveLength(1)
  await act(async () => { cleared = true; complete(new Response(null, { status: 204 })) })
  expect(await screen.findByText(MESSAGES.questionHistoryEmpty)).toBeInTheDocument()
})

it('waits for an in-flight question before allowing history to be cleared', async () => {
  let complete!: (value: Response) => void
  const pending = new Promise<Response>((resolve) => { complete = resolve })
  fetchMock.mockImplementation((url, options) => url === endpoint && options?.method === 'POST' ? pending : standardFetch(url, options))
  show()
  fireEvent.change(await screen.findByRole('textbox', { name: 'Question *' }), { target: { value: 'Question in progress' } })
  fireEvent.click(screen.getByRole('button', { name: 'Ask question' }))
  expect(screen.getByRole('button', { name: 'Clear Q&A history' })).toBeDisabled()
  expect(screen.getByText(MESSAGES.questionHistoryClearBusy)).toBeInTheDocument()
  await act(async () => complete(json({ target_id: target.id, status: 'answered', answer: 'Finished answer', review_count: 1 })))
  expect(screen.getByRole('button', { name: 'Clear Q&A history' })).toBeEnabled()
})

it.each(['resolve', 'reject'])('ignores old clear completion after target navigation (%s)', async (outcome) => {
  let complete!: (value: Response) => void
  let fail!: (reason: Error) => void
  const pending = new Promise<Response>((resolve, reject) => { complete = resolve; fail = reject })
  fetchMock.mockImplementation((url, options) => options?.method === 'DELETE' ? pending : standardFetch(url, options))
  show()
  const dialog = await confirmDialog()
  fireEvent.click(within(dialog).getByRole('button', { name: 'Clear Q&A history' }))
  fireEvent.click(screen.getByRole('link', { name: 'Open service analysis' }))
  expect(await screen.findByText('Service center question')).toBeInTheDocument()
  await act(async () => outcome === 'resolve' ? complete(new Response(null, { status: 204 })) : fail(new TypeError('private error')))
  expect(screen.getByText('Service center question')).toBeInTheDocument()
  expect(screen.queryByText(MESSAGES.questionHistoryCleared)).not.toBeInTheDocument()
  expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  expect(deleteCalls()[0][1]?.signal?.aborted).toBe(true)
})
