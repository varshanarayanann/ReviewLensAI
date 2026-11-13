import { act, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { expect, it, vi } from 'vitest'
import App from '../App'
import { MESSAGES } from '../lib/messages'
import { createFakeAuth, fakeSession } from '../test/fakeAuth'

const config = { apiBaseUrl: 'http://api.test', supabaseUrl: 'https://auth.test', supabaseAnonKey: 'public' }
const target = { id: 'target-a', name: 'Cafe', platform: 'google_maps', source_url: 'https://google.com/maps/place/Cafe' }
const endpoint = 'http://api.test/api/targets/target-a/ingestions/google-maps'
const result = { target_id: target.id, run_id: 'run-a', state: 'succeeded', persisted_count: 2, rejected_count: 0, message: 'Imported 2 reviews; rejected 0 records.' }
const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status })

function workspaceResponse(url: string, count = 0) {
  if (url.endsWith('/latest')) return json(null)
  if (url.endsWith('/summary')) return json({ target_id: target.id, review_count: count, average_rating: count ? 5 : null })
  return json(target)
}

function showWorkspace() {
  render(<MemoryRouter initialEntries={['/targets/target-a']}>
    <App config={config} authClient={createFakeAuth(fakeSession()).client} />
  </MemoryRouter>)
}

it('collects from the saved source and reloads the persisted review summary', async () => {
  let saved = false
  const fetchMock = vi.fn((url: string) => {
    if (url === endpoint) { saved = true; return Promise.resolve(json(result)) }
    return Promise.resolve(workspaceResponse(url, saved ? 2 : 0))
  })
  vi.stubGlobal('fetch', fetchMock)
  showWorkspace()
  fireEvent.click(await screen.findByRole('button', { name: 'Ingest reviews' }))
  expect(await screen.findByText(result.message)).toBeInTheDocument()
  expect(await screen.findByText('2 reviews')).toBeInTheDocument()
  expect(screen.getByText('Ingested')).toBeInTheDocument()
  expect(fetchMock).toHaveBeenCalledWith(endpoint, expect.objectContaining({
    method: 'POST', body: '{}',
    headers: expect.objectContaining({ Authorization: 'Bearer test-access-token' }),
  }))
})

it('blocks repeated collection and refresh while the provider is pending', async () => {
  let complete!: (response: Response) => void
  const pending = new Promise<Response>((resolve) => { complete = resolve })
  const fetchMock = vi.fn((url: string) => url === endpoint
    ? pending : Promise.resolve(workspaceResponse(url)))
  vi.stubGlobal('fetch', fetchMock)
  showWorkspace()
  const button = await screen.findByRole('button', { name: 'Ingest reviews' })
  fireEvent.click(button)
  fireEvent.click(button)
  expect(screen.getByRole('button', { name: 'Ingesting...' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Refresh workspace' })).toBeDisabled()
  expect(screen.getByText(MESSAGES.mapsCollectionBusy)).toBeInTheDocument()
  expect(fetchMock.mock.calls.filter(([url]) => url === endpoint)).toHaveLength(1)
  await act(async () => complete(json(result)))
})

it.each([503, 0])('shows a safe collection error (%s) and allows retry', async (status) => {
  vi.stubGlobal('fetch', vi.fn((url: string) => {
    if (url !== endpoint) return Promise.resolve(workspaceResponse(url))
    return status ? Promise.resolve(json({ detail: 'secret provider details' }, status))
      : Promise.reject(new TypeError('secret network details'))
  }))
  showWorkspace()
  fireEvent.click(await screen.findByRole('button', { name: 'Ingest reviews' }))
  expect(await screen.findByRole('alert')).toHaveTextContent(status ? MESSAGES.mapsCollectionFailed : MESSAGES.offline)
  expect(screen.queryByText('secret provider details')).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Ingest reviews' })).toBeEnabled()
})

it.each([[401, 'Log in'], [404, 'Analysis target not found']])(
  'handles an authorization failure during collection (%s)', async (status, heading) => {
    vi.stubGlobal('fetch', vi.fn((url: string) => Promise.resolve(url === endpoint
      ? json({}, status) : workspaceResponse(url))))
    showWorkspace()
    fireEvent.click(await screen.findByRole('button', { name: 'Ingest reviews' }))
    expect(await screen.findByRole('heading', { name: heading })).toBeInTheDocument()
  },
)

it('shows a recorded failed collection and retains the saved dataset', async () => {
  vi.stubGlobal('fetch', vi.fn((url: string) => Promise.resolve(url === endpoint
    ? json({ ...result, state: 'failed', persisted_count: 0, message: 'Reviews could not be collected. Try again shortly.' })
    : workspaceResponse(url, 3))))
  showWorkspace()
  expect(await screen.findByText('3 reviews')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Ingest reviews' }))
  expect(await screen.findByText('Failed')).toBeInTheDocument()
  expect(screen.getByText('3 reviews')).toBeInTheDocument()
})
