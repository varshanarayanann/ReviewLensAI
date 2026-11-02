import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, expect, it, vi } from 'vitest'
import App from '../App'
import { MESSAGES } from '../lib/messages'
import { createFakeAuth, fakeSession } from '../test/fakeAuth'

const config = { apiBaseUrl: 'http://api.test', supabaseUrl: 'https://auth.test', supabaseAnonKey: 'public' }
const target = {
  id: 'target-a', name: 'A private business', platform: 'google_maps',
  source_url: 'https://google.com/maps/place/A', created_at: '2026-01-01T12:00:00Z',
}
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status })
let fetchMock: ReturnType<typeof vi.fn>

beforeEach(() => {
  fetchMock = vi.fn().mockResolvedValue(json([target]))
  vi.stubGlobal('fetch', fetchMock)
})

function showDashboard() {
  const fake = createFakeAuth(fakeSession())
  render(<MemoryRouter initialEntries={['/dashboard']}><App config={config} authClient={fake.client} /></MemoryRouter>)
  return fake
}

it('shows the name, platform, source, and workspace link from the owned target response', async () => {
  showDashboard()
  const link = await screen.findByRole('link', { name: `Open ${target.name}` })
  expect(link).toHaveAttribute('href', '/targets/target-a')
  expect(link).toHaveTextContent('Google Maps')
  expect(link).toHaveTextContent(target.source_url)
  expect(screen.getByRole('link', { name: 'New target' })).toHaveAttribute('href', '/targets/new')
  expect(fetchMock).toHaveBeenCalledWith('http://api.test/api/targets', {
    headers: { Authorization: 'Bearer test-access-token' },
  })
  fetchMock.mockImplementation((url: string) => Promise.resolve(json(
    url.endsWith('/latest') ? null : target,
  )))
  fireEvent.click(link)
  expect(await screen.findByRole('heading', { name: target.name })).toBeInTheDocument()
  expect(screen.getByText('Not ingested')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Upload reviews' })).toBeEnabled()
})

it('shows an actionable empty state', async () => {
  fetchMock.mockResolvedValue(json([]))
  showDashboard()
  expect(await screen.findByRole('heading', { name: MESSAGES.noTargets })).toBeInTheDocument()
  expect(screen.getByText(MESSAGES.addTarget)).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'New target' })).toBeInTheDocument()
})

it('shows loading while the list request is pending', async () => {
  fetchMock.mockReturnValue(new Promise(() => {}))
  showDashboard()
  expect(await screen.findByLabelText('Loading analysis targets')).toHaveAttribute('aria-busy', 'true')
  expect(screen.queryByText(MESSAGES.noTargets)).not.toBeInTheDocument()
})

it.each([
  [503, MESSAGES.unexpected],
  [0, MESSAGES.offline],
])('maps failure %s safely and supports retry', async (status, message) => {
  if (status === 0) fetchMock.mockRejectedValue(new Error('sensitive transport detail'))
  else fetchMock.mockResolvedValue(json({ detail: 'sensitive server detail' }, status))
  showDashboard()
  expect(await screen.findByRole('alert')).toHaveTextContent(message)
  expect(screen.queryByText(/sensitive/)).not.toBeInTheDocument()
  fetchMock.mockResolvedValue(json([target]))
  fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
  expect(await screen.findByText(target.name)).toBeInTheDocument()
})

it('expires the session on a rejected access token', async () => {
  fetchMock.mockResolvedValue(json({ detail: 'raw auth detail' }, 401))
  const fake = showDashboard()
  expect(await screen.findByText(MESSAGES.sessionEnded)).toBeInTheDocument()
  expect(fake.auth.signOut).toHaveBeenCalled()
  expect(screen.queryByText('raw auth detail')).not.toBeInTheDocument()
})

it('clears previous targets immediately when the authenticated user changes', async () => {
  const fake = showDashboard()
  await screen.findByText(target.name)
  let resolveB!: (response: Response) => void
  fetchMock.mockReturnValue(new Promise<Response>((resolve) => { resolveB = resolve }))
  const next = fakeSession('b@example.com')
  next.user.id = 'user-b-id'
  next.access_token = 'token-b'
  act(() => fake.emit('SIGNED_IN', next))
  expect(screen.queryByText(target.name)).not.toBeInTheDocument()
  await waitFor(() => expect(fetchMock).toHaveBeenLastCalledWith('http://api.test/api/targets', {
    headers: { Authorization: 'Bearer token-b' },
  }))
  await act(async () => resolveB(json([{ ...target, id: 'target-b', name: 'B private business' }])))
  expect(await screen.findByText('B private business')).toBeInTheDocument()
  expect(screen.queryByText(target.name)).not.toBeInTheDocument()
})

it('ignores a late response from the previous user', async () => {
  let resolveA!: (response: Response) => void
  fetchMock.mockReturnValueOnce(new Promise<Response>((resolve) => { resolveA = resolve }))
  const fake = showDashboard()
  await screen.findByLabelText('Loading analysis targets')
  fetchMock.mockResolvedValue(json([]))
  const next = fakeSession('b@example.com')
  next.user.id = 'user-b-id'
  act(() => fake.emit('SIGNED_IN', next))
  await screen.findByText(MESSAGES.noTargets)
  await act(async () => resolveA(json([target])))
  expect(screen.queryByText(target.name)).not.toBeInTheDocument()
})
