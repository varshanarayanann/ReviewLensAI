import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { Link, MemoryRouter } from 'react-router'
import { beforeEach, expect, it, vi } from 'vitest'
import App from '../App'
import { AnalysisTargetWorkspaceView } from '../components/workspace/AnalysisTargetWorkspaceView'
import { MESSAGES } from '../lib/messages'
import { createFakeAuth, fakeSession } from '../test/fakeAuth'

const config = { apiBaseUrl: 'http://api.test', supabaseUrl: 'https://auth.test', supabaseAnonKey: 'public' }
const target = { id: 'target-a', name: 'Example Cafe', platform: 'google_maps', source_url: 'https://google.com/maps/place/Cafe' }
const succeeded = { run_id: 'run-a', target_id: target.id, state: 'succeeded', persisted_count: 1, message: 'Ingested 1 reviews.' }
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status })
let fetchMock: ReturnType<typeof vi.fn>

beforeEach(() => {
  fetchMock = vi.fn((url: string) => Promise.resolve(json(url.endsWith('/latest') ? null : target)))
  vi.stubGlobal('fetch', fetchMock)
})

function showWorkspace(path = '/targets/target-a', fake = createFakeAuth(fakeSession())) {
  render(<MemoryRouter initialEntries={[path]}>
    <Link to="/targets/target-b">Open another target</Link>
    <App config={config} authClient={fake.client} />
  </MemoryRouter>)
  return fake
}

function chooseFile(name = 'reviews.csv', contents = 'rating,review_text\n5,Great') {
  const file = new File([contents], name, { type: 'text/csv' })
  Object.defineProperty(file, 'text', { value: vi.fn().mockResolvedValue(contents) })
  fireEvent.change(screen.getByLabelText('Reviews CSV file *'), { target: { files: [file] } })
  return file
}

it('requires authentication before loading any target data', async () => {
  showWorkspace('/targets/target-a', createFakeAuth())
  expect(await screen.findByRole('heading', { name: 'Log in' })).toBeInTheDocument()
  expect(fetchMock).not.toHaveBeenCalled()
})

it('loads the authorized target, real platform, source link, and no-run state', async () => {
  showWorkspace()
  expect(await screen.findByRole('heading', { name: target.name })).toBeInTheDocument()
  expect(screen.getByText('Google Maps')).toBeInTheDocument()
  expect(screen.getByRole('link', { name: target.source_url })).toHaveAttribute('rel', 'noopener noreferrer')
  expect(screen.getByText('Not ingested')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Upload reviews' })).toBeEnabled()
  expect(fetchMock).toHaveBeenNthCalledWith(1, 'http://api.test/api/targets/target-a', expect.objectContaining({
    headers: expect.objectContaining({ Authorization: 'Bearer test-access-token' }),
  }))
  expect(fetchMock).toHaveBeenNthCalledWith(2, 'http://api.test/api/targets/target-a/ingestions/latest', expect.anything())
  expect(screen.queryByText(/S1-019 backend integration/)).not.toBeInTheDocument()
})

it('shows a loading state without an ingestion action while data is pending', async () => {
  fetchMock.mockImplementation(() => new Promise(() => {}))
  showWorkspace()
  expect(await screen.findByLabelText('Loading workspace')).toHaveAttribute('aria-busy', 'true')
  expect(screen.queryByRole('button', { name: 'Upload reviews' })).not.toBeInTheDocument()
})

it.each([[403], [404]])('maps access response %s to the same safe unavailable state', async (status) => {
  fetchMock.mockImplementation(() => Promise.resolve(json({ detail: 'private raw detail' }, status)))
  showWorkspace()
  expect(await screen.findByRole('alert')).toHaveTextContent(MESSAGES.targetNotFound)
  expect(screen.queryByText(target.name)).not.toBeInTheDocument()
  expect(screen.queryByText('private raw detail')).not.toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Upload reviews' })).not.toBeInTheDocument()
  expect(fetchMock).toHaveBeenCalledTimes(1)
})

it('shows safe load failure and refreshes successfully', async () => {
  fetchMock.mockImplementationOnce(() => Promise.reject(new Error('sensitive network detail')))
  showWorkspace()
  expect(await screen.findByRole('alert')).toHaveTextContent(MESSAGES.offline)
  fireEvent.click(screen.getByRole('button', { name: 'Refresh workspace' }))
  expect(await screen.findByRole('heading', { name: target.name })).toBeInTheDocument()
  expect(screen.queryByText(/sensitive/)).not.toBeInTheDocument()
})

it('ends the session on a rejected workspace request', async () => {
  fetchMock.mockImplementation(() => Promise.resolve(json({}, 401)))
  const fake = showWorkspace()
  expect(await screen.findByText(MESSAGES.sessionEnded)).toBeInTheDocument()
  expect(fake.auth.signOut).toHaveBeenCalled()
})

it.each([
  ['processing', 'Ingesting'],
  ['succeeded', 'Ingested'],
  ['partial', 'Partially ingested'],
  ['failed', 'Failed'],
])('restores persisted ingestion state %s', async (state, label) => {
  fetchMock.mockImplementation((url: string) => Promise.resolve(json(url.endsWith('/latest')
    ? { ...succeeded, state, message: 'Recorded result', persisted_count: state === 'succeeded' ? 1 : 0 } : target)))
  showWorkspace()
  expect(await screen.findByText(label)).toBeInTheDocument()
  expect(screen.getByText('Recorded result')).toBeInTheDocument()
  if (state === 'processing') expect(screen.getByRole('button', { name: 'Upload reviews' })).toBeDisabled()
})

it('uploads to the active target and displays the persisted result after refresh', async () => {
  let saved = false
  fetchMock.mockImplementation((url: string, options?: RequestInit) => {
    if (options?.method === 'POST') { saved = true; return Promise.resolve(json(succeeded)) }
    return Promise.resolve(json(url.endsWith('/latest') ? (saved ? succeeded : null) : target))
  })
  showWorkspace()
  await screen.findByRole('heading', { name: target.name })
  chooseFile()
  fireEvent.click(screen.getByRole('button', { name: 'Upload reviews' }))
  expect(await screen.findByText('Ingested')).toBeInTheDocument()
  expect(fetchMock).toHaveBeenCalledWith('http://api.test/api/targets/target-a/ingestions', expect.objectContaining({
    method: 'POST', body: JSON.stringify({ csv_text: 'rating,review_text\n5,Great' }),
  }))
  fireEvent.click(screen.getByRole('button', { name: 'Refresh workspace' }))
  expect(await screen.findByText(succeeded.message)).toBeInTheDocument()
})

it('validates and focuses the file input without sending invalid CSV selections', async () => {
  showWorkspace()
  await screen.findByRole('heading', { name: target.name })
  chooseFile('reviews.txt')
  fireEvent.click(screen.getByRole('button', { name: 'Upload reviews' }))
  expect(screen.getByRole('alert')).toHaveTextContent(MESSAGES.csvFile)
  expect(screen.getByLabelText('Reviews CSV file *')).toHaveFocus()
  expect(fetchMock).toHaveBeenCalledTimes(2)
})

it('maps rejected CSV sources to safe guidance and retains the selected file', async () => {
  fetchMock.mockImplementation((url: string, options?: RequestInit) => Promise.resolve(
    options?.method === 'POST'
      ? json({ detail: 'private parser detail' }, 422)
      : json(url.endsWith('/latest') ? null : target),
  ))
  showWorkspace()
  await screen.findByRole('heading', { name: target.name })
  const file = chooseFile()
  fireEvent.submit(screen.getByRole('button', { name: 'Upload reviews' }).closest('form')!)
  expect(await screen.findByRole('alert')).toHaveTextContent(MESSAGES.csvFormat)
  expect(screen.queryByText('private parser detail')).not.toBeInTheDocument()
  expect(screen.getByLabelText('Reviews CSV file *')).toHaveProperty('files', [file])
})

it('keeps the authorized target context on a failed import', async () => {
  fetchMock.mockImplementation((url: string, options?: RequestInit) => Promise.resolve(json(
    options?.method === 'POST' ? { ...succeeded, state: 'failed', persisted_count: 0, message: 'Reviews could not be collected. Try again shortly.' }
      : url.endsWith('/latest') ? null : target,
  )))
  showWorkspace()
  await screen.findByRole('heading', { name: target.name })
  chooseFile()
  fireEvent.click(screen.getByRole('button', { name: 'Upload reviews' }))
  expect(await screen.findByText('Failed')).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: target.name })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Upload reviews' })).toBeEnabled()
})

it('restores a failed ingestion result after refreshing the workspace', async () => {
  const failed = {
    ...succeeded,
    state: 'failed',
    persisted_count: 0,
    message: 'Reviews could not be collected. Try again shortly.',
  }

  let saved = false

  fetchMock.mockImplementation((url: string, options?: RequestInit) => {
    if (options?.method === 'POST') {
      saved = true
      return Promise.resolve(json(failed))
    }

    return Promise.resolve(
      json(url.endsWith('/latest') ? (saved ? failed : null) : target),
    )
  })

  showWorkspace()
  await screen.findByRole('heading', { name: target.name })

  chooseFile()
  fireEvent.click(screen.getByRole('button', { name: 'Upload reviews' }))

  expect(await screen.findByText('Failed')).toBeInTheDocument()

  fireEvent.click(screen.getByRole('button', { name: 'Refresh workspace' }))

  expect(await screen.findByText(failed.message)).toBeInTheDocument()
  expect(screen.getByText('Failed')).toBeInTheDocument()
})

it('blocks duplicate imports while a submission is pending', async () => {
  fetchMock.mockImplementation((url: string, options?: RequestInit) => options?.method === 'POST'
    ? new Promise(() => {}) : Promise.resolve(json(url.endsWith('/latest') ? null : target)))
  showWorkspace()
  await screen.findByRole('heading', { name: target.name })
  chooseFile()
  fireEvent.click(screen.getByRole('button', { name: 'Upload reviews' }))
  expect(await screen.findByRole('button', { name: 'Uploading...' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Refresh workspace' })).toBeDisabled()
  await waitFor(() => expect(fetchMock.mock.calls.filter(([, options]) => options?.method === 'POST')).toHaveLength(1))
})

it.each([
  [401, MESSAGES.sessionEnded], [403, MESSAGES.targetNotFound],
  [422, MESSAGES.csvFormat], [500, MESSAGES.unexpected],
])('handles upload response %s without exposing raw details', async (status, message) => {
  fetchMock.mockImplementation((url: string, options?: RequestInit) => Promise.resolve(
    options?.method === 'POST' ? json({ detail: 'sensitive upload error' }, status)
      : json(url.endsWith('/latest') ? null : target),
  ))
  showWorkspace()
  await screen.findByRole('heading', { name: target.name })
  chooseFile()
  fireEvent.click(screen.getByRole('button', { name: 'Upload reviews' }))
  expect(await screen.findByText(message)).toBeInTheDocument()
  expect(screen.queryByText('sensitive upload error')).not.toBeInTheDocument()
  if (status === 403) expect(screen.queryByRole('button', { name: 'Upload reviews' })).not.toBeInTheDocument()
})

it('does not submit an old file after navigating away during its read', async () => {
  showWorkspace()
  await screen.findByRole('heading', { name: target.name })
  const file = new File(['rating,review_text\n5,Great'], 'reviews.csv')
  let resolveText!: (text: string) => void
  Object.defineProperty(file, 'text', { value: () => new Promise<string>((resolve) => { resolveText = resolve }) })
  fireEvent.change(screen.getByLabelText('Reviews CSV file *'), { target: { files: [file] } })
  fireEvent.click(screen.getByRole('button', { name: 'Upload reviews' }))
  fireEvent.click(screen.getByRole('link', { name: 'Open another target' }))
  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('http://api.test/api/targets/target-b', expect.anything()))
  await act(async () => resolveText('rating,review_text\n5,Great'))
  expect(fetchMock.mock.calls.some(([, options]) => options?.method === 'POST')).toBe(false)
})

it('clears the old context when navigating to a different target and ignores late responses', async () => {
  let resolveOld!: (response: Response) => void
  fetchMock.mockImplementation((url: string) => url.includes('target-a')
    ? new Promise<Response>((resolve) => { resolveOld = resolve })
    : Promise.resolve(json(url.endsWith('/latest') ? null : { ...target, id: 'target-b', name: 'Other target' })))
  showWorkspace()
  await screen.findByLabelText('Loading workspace')
  fireEvent.click(screen.getByRole('link', { name: 'Open another target' }))
  await screen.findByRole('heading', { name: 'Other target' })
  await act(async () => resolveOld(json(target)))
  expect(screen.queryByText(target.name)).not.toBeInTheDocument()
})

it('hides target context immediately when the authenticated user changes', async () => {
  const fake = showWorkspace()
  await screen.findByRole('heading', { name: target.name })
  fetchMock.mockImplementation(() => Promise.resolve(json({}, 404)))
  const next = fakeSession('other@example.com')
  next.user.id = 'user-b'
  act(() => fake.emit('SIGNED_IN', next))
  expect(screen.queryByText(target.name)).not.toBeInTheDocument()
  expect(await screen.findByRole('alert')).toHaveTextContent(MESSAGES.targetNotFound)
})

it('renders forbidden and missing presentation identically', () => {
  const view = (kind: 'missing' | 'forbidden') => <MemoryRouter><AnalysisTargetWorkspaceView state={{ kind }} /></MemoryRouter>
  const { container, rerender } = render(view('missing'))
  const missing = container.innerHTML
  rerender(view('forbidden'))
  expect(container.innerHTML).toBe(missing)
})
