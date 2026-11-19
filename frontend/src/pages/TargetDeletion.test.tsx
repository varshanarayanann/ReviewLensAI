import { stubFetchWithEmptyHistory } from '../test/emptyHistory'
import { act, fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import App from '../App'
import { MESSAGES } from '../lib/messages'
import { createFakeAuth, fakeSession } from '../test/fakeAuth'

const config = { apiBaseUrl: 'http://api.test', supabaseUrl: 'https://auth.test', supabaseAnonKey: 'public' }
const target = { id: 'target-a', name: 'Cafe', platform: 'google_maps', source_url: 'https://google.com/maps/place/Cafe' }
const targetUrl = 'http://api.test/api/targets/target-a'
const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status })
let fetchMock: ReturnType<typeof vi.fn<(url: string, options?: RequestInit) => Promise<Response>>>

beforeEach(() => {
  // jsdom lacks the browser's native modal methods.
  Object.defineProperty(HTMLDialogElement.prototype, 'showModal', {
    configurable: true, value: function (this: HTMLDialogElement) { this.open = true },
  })
  Object.defineProperty(HTMLDialogElement.prototype, 'close', {
    configurable: true, value: function (this: HTMLDialogElement) { this.open = false },
  })
  fetchMock = vi.fn((url: string, options?: RequestInit) => {
    if (options?.method === 'DELETE') return Promise.resolve(new Response(null, { status: 204 }))
    if (url.endsWith('/latest')) return Promise.resolve(json(null))
    if (url.endsWith('/summary')) return Promise.resolve(json({ target_id: target.id, review_count: 0, average_rating: null }))
    if (url.endsWith('/api/targets')) return Promise.resolve(json([]))
    return Promise.resolve(json(target))
  })
  stubFetchWithEmptyHistory(fetchMock)
})

afterEach(() => {
  Reflect.deleteProperty(HTMLDialogElement.prototype, 'showModal')
  Reflect.deleteProperty(HTMLDialogElement.prototype, 'close')
})

function showWorkspace() {
  render(<MemoryRouter initialEntries={['/targets/target-a']}>
    <App config={config} authClient={createFakeAuth(fakeSession()).client} />
  </MemoryRouter>)
}

async function openConfirmation() {
  const actions = await screen.findByText('Target actions')
  fireEvent.click(actions)
  actions.closest('details')!.open = true
  fireEvent.click(screen.getByRole('button', { name: 'Delete target' }))
  return screen.getByRole('dialog', { name: 'Delete “Cafe”?' })
}

it('requires confirmation and restores focus on cancel or Escape', async () => {
  showWorkspace()
  let dialog = await openConfirmation()
  expect(within(dialog).getByRole('button', { name: 'Cancel' })).toHaveFocus()
  expect(fetchMock.mock.calls.some(([, options]) => options?.method === 'DELETE')).toBe(false)
  fireEvent.click(within(dialog).getByRole('button', { name: 'Cancel' }))
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Delete target' })).toHaveFocus()
  fireEvent.click(screen.getByRole('button', { name: 'Delete target' }))
  dialog = screen.getByRole('dialog')
  fireEvent(dialog, new Event('cancel', { bubbles: true, cancelable: true }))
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
})

it('deletes the active target after confirmation and returns to the dashboard', async () => {
  showWorkspace()
  const dialog = await openConfirmation()
  fireEvent.click(within(dialog).getByRole('button', { name: 'Delete target' }))
  expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
  expect(fetchMock).toHaveBeenCalledWith(targetUrl, expect.objectContaining({
    method: 'DELETE', headers: { Authorization: 'Bearer test-access-token' },
  }))
})

it.each([
  [409, MESSAGES.targetDeleteBusy],
  [503, MESSAGES.targetDeleteFailed],
  [0, MESSAGES.offline],
])('preserves the target and shows a safe deletion error (%s)', async (status, expected) => {
  const normalFetch = fetchMock.getMockImplementation()!
  fetchMock.mockImplementation((url: string, options?: RequestInit) => {
    if (options?.method !== 'DELETE') return normalFetch(url, options)
    return status ? Promise.resolve(json({ detail: 'private error' }, status))
      : Promise.reject(new TypeError('private network error'))
  })
  showWorkspace()
  const dialog = await openConfirmation()
  fireEvent.click(within(dialog).getByRole('button', { name: 'Delete target' }))
  expect(await within(dialog).findByRole('alert')).toHaveTextContent(expected)
  expect(screen.getByRole('heading', { name: 'Cafe' })).toBeInTheDocument()
  expect(screen.queryByText('private error')).not.toBeInTheDocument()
})

it.each([[401, 'Log in'], [404, 'Analysis target not found']])(
  'handles access failure safely (%s)', async (status, heading) => {
    const normalFetch = fetchMock.getMockImplementation()!
    fetchMock.mockImplementation((url: string, options?: RequestInit) => options?.method === 'DELETE'
      ? Promise.resolve(json({}, status)) : normalFetch(url, options))
    showWorkspace()
    const dialog = await openConfirmation()
    fireEvent.click(within(dialog).getByRole('button', { name: 'Delete target' }))
    expect(await screen.findByRole('heading', { name: heading })).toBeInTheDocument()
  },
)

it('prevents duplicate deletion and cancellation while the request is pending', async () => {
  let complete!: (response: Response) => void
  const pending = new Promise<Response>((resolve) => { complete = resolve })
  const normalFetch = fetchMock.getMockImplementation()!
  fetchMock.mockImplementation((url: string, options?: RequestInit) => options?.method === 'DELETE'
    ? pending : normalFetch(url, options))
  showWorkspace()
  const dialog = await openConfirmation()
  const button = within(dialog).getByRole('button', { name: 'Delete target' })
  fireEvent.click(button)
  fireEvent.click(button)
  fireEvent(dialog, new Event('cancel', { bubbles: true, cancelable: true }))
  expect(within(dialog).getByRole('button', { name: 'Deleting...' })).toBeDisabled()
  expect(within(dialog).getByRole('button', { name: 'Cancel' })).toBeDisabled()
  expect(fetchMock.mock.calls.filter(([, options]) => options?.method === 'DELETE')).toHaveLength(1)
  await act(async () => complete(new Response(null, { status: 204 })))
})
