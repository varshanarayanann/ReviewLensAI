import { act, fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter, useNavigate } from 'react-router'
import { expect, it, vi } from 'vitest'
import App from '../App'
import { MESSAGES } from '../lib/messages'
import { createFakeAuth, fakeSession } from '../test/fakeAuth'

const config = { apiBaseUrl: 'http://api.test', supabaseUrl: 'https://auth.test', supabaseAnonKey: 'public' }
const targetsUrl = `${config.apiBaseUrl}/api/targets`
const cafe = { id: 'cafe', name: 'Cafe', platform: 'google_maps', source_url: 'https://google.com/maps/place/Cafe' }
const library = { id: 'library', name: 'Library', platform: 'google_maps', source_url: 'https://google.com/maps/place/Library' }
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status })

function workspaceResponse(url: string) {
  if (url.startsWith(`${targetsUrl}/other-user`)) return json({}, 404)
  const target = url.startsWith(`${targetsUrl}/library`) ? library : cafe
  if (url.endsWith('/ingestions/latest')) {
    return json(target === library
      ? { run_id: 'library-run', target_id: library.id, state: 'succeeded', persisted_count: 4, rejected_count: 0, message: 'Imported 4 reviews.' }
      : null)
  }
  if (url.endsWith('/reviews/summary')) {
    return json(target === library
      ? { target_id: library.id, review_count: 4, average_rating: 4.5 }
      : { target_id: cafe.id, review_count: 1, average_rating: 2 })
  }
  return json(target)
}

function BackButton() {
  const navigate = useNavigate()
  return <button onClick={() => void navigate(-1)}>Browser back</button>
}

function showWorkspace(path = '/targets/cafe') {
  render(<MemoryRouter initialEntries={[path]}>
    <App config={config} authClient={createFakeAuth(fakeSession()).client} />
    <BackButton />
  </MemoryRouter>)
}

async function openSwitcher() {
  fireEvent.click(await screen.findByRole('button', { name: 'Switch target' }))
  return within(screen.getByRole('navigation', { name: 'Switch analysis target' }))
}

it('switches to an owned target and reloads its workspace and summary', async () => {
  const fetchMock = vi.fn((url: string) => Promise.resolve(url === targetsUrl
    ? json([cafe, library]) : workspaceResponse(url)))
  vi.stubGlobal('fetch', fetchMock)
  showWorkspace()
  expect(await screen.findByText('1 review')).toBeInTheDocument()
  expect(fetchMock.mock.calls.some(([url]) => url === targetsUrl)).toBe(false)

  const switcher = await openSwitcher()
  expect(switcher.queryByRole('link', { name: /^Cafe/ })).not.toBeInTheDocument()
  const destination = await switcher.findByRole('link', { name: /^Library/ })
  expect(fetchMock).toHaveBeenCalledWith(targetsUrl, expect.objectContaining({
    headers: { Authorization: 'Bearer test-access-token' },
  }))
  fireEvent.click(destination)
  expect(await screen.findByRole('heading', { name: 'Library' })).toBeInTheDocument()
  expect(screen.getByRole('link', { name: library.source_url })).toBeInTheDocument()
  expect(screen.getByText('Ingested')).toBeInTheDocument()
  expect(await screen.findByText('4 reviews')).toBeInTheDocument()
  expect(screen.getByText('4.5 / 5')).toBeInTheDocument()
  expect(screen.queryByText('1 review')).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Switch target' })).toHaveAttribute('aria-expanded', 'false')

  fireEvent.click(screen.getByRole('button', { name: 'Browser back' }))
  expect(await screen.findByRole('heading', { name: 'Cafe' })).toBeInTheDocument()
  expect(await screen.findByText('1 review')).toBeInTheDocument()
})

it('reports when the active target is the only owned target', async () => {
  vi.stubGlobal('fetch', vi.fn((url: string) => Promise.resolve(url === targetsUrl
    ? json([cafe]) : workspaceResponse(url))))
  showWorkspace()
  const switcher = await openSwitcher()
  expect(await switcher.findByText(MESSAGES.noOtherTargets)).toBeInTheDocument()
  expect(switcher.queryByRole('link')).not.toBeInTheDocument()
})

it('keeps the workspace available while the target list loads and after a list error', async () => {
  let finish!: (response: Response) => void
  const pending = new Promise<Response>((resolve) => { finish = resolve })
  const listRequest = vi.fn().mockReturnValueOnce(pending).mockResolvedValueOnce(json([cafe, library]))
  vi.stubGlobal('fetch', vi.fn((url: string) => url === targetsUrl
    ? listRequest() : Promise.resolve(workspaceResponse(url))))
  showWorkspace()
  const switcher = await openSwitcher()
  expect(switcher.getByRole('status')).toHaveTextContent('Loading analysis targets')
  await act(async () => finish(json({ detail: 'private details' }, 503)))
  expect(switcher.getByRole('alert')).toHaveTextContent(MESSAGES.targetSwitchUnavailable)
  expect(screen.queryByText('private details')).not.toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'Cafe' })).toBeInTheDocument()
  fireEvent.click(switcher.getByRole('button', { name: 'Retry loading targets' }))
  expect(await switcher.findByRole('link', { name: /^Library/ })).toBeInTheDocument()
})

it('keeps another user’s target unavailable when opened directly', async () => {
  const fetchMock = vi.fn((url: string) => Promise.resolve(workspaceResponse(url)))
  vi.stubGlobal('fetch', fetchMock)
  showWorkspace('/targets/other-user')
  expect(await screen.findByRole('heading', { name: 'Analysis target not found' })).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Switch target' })).not.toBeInTheDocument()
  expect(fetchMock).toHaveBeenCalledTimes(1)
})
