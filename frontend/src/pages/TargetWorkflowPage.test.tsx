import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { expect, it, vi } from 'vitest'
import App from '../App'
import { createFakeAuth, fakeSession } from '../test/fakeAuth'

const config = { apiBaseUrl: 'http://api.test', supabaseUrl: 'http://auth.test', supabaseAnonKey: 'public' }

it('maps backend validation failures and preserves input', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{}', { status: 422 })))
  render(<MemoryRouter initialEntries={['/targets/new']}><App config={config} authClient={createFakeAuth(fakeSession()).client} /></MemoryRouter>)
  await screen.findByRole('heading', { name: 'Create target' })
  fireEvent.change(screen.getByLabelText('Target name *'), { target: { value: 'Example' } })
  fireEvent.change(screen.getByLabelText('Google Maps URL *'), { target: { value: 'https://bad.example/' } })
  fireEvent.click(screen.getByRole('button', { name: 'Create target' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('valid HTTPS Google Maps')
  expect(screen.getByLabelText('Target name *')).toHaveValue('Example')
})

it('restores a recorded failed ingestion with target context', async () => {
  vi.stubGlobal('fetch', vi.fn((url: string) => Promise.resolve(new Response(JSON.stringify(
    url.endsWith('/latest') ? { state: 'failed', persisted_count: 0, message: 'Reviews could not be collected. Try again shortly.' }
      : url.endsWith('/reviews/summary')
        ? { target_id: 'target-id', review_count: 0, average_rating: null }
        : { id: 'target-id', name: 'Example business', platform: 'google_maps', source_url: 'https://google.com/maps/place/X' },
  )))))
  render(<MemoryRouter initialEntries={['/targets/target-id']}><App config={config} authClient={createFakeAuth(fakeSession()).client} /></MemoryRouter>)
  expect(await screen.findByRole('alert')).toHaveTextContent('Try again')
  expect(await screen.findByRole('heading', { name: 'Example business' })).toBeInTheDocument()
})

it('opens the workspace for a newly created target', async () => {
  vi.stubGlobal('fetch', vi.fn((url: string, options?: RequestInit) => Promise.resolve(new Response(JSON.stringify(
    options?.method === 'POST' ? { id: 'created-target' } : url.endsWith('/latest') ? null
      : url.endsWith('/reviews/summary')
        ? { target_id: 'created-target', review_count: 0, average_rating: null }
        : { id: 'created-target', name: 'Created business', platform: 'google_maps', source_url: 'https://google.com/maps/place/X' },
  )))))
  render(<MemoryRouter initialEntries={['/targets/new']}><App config={config} authClient={createFakeAuth(fakeSession()).client} /></MemoryRouter>)
  await screen.findByRole('heading', { name: 'Create target' })
  fireEvent.change(screen.getByLabelText('Target name *'), { target: { value: 'Created business' } })
  fireEvent.change(screen.getByLabelText('Google Maps URL *'), { target: { value: 'https://google.com/maps/place/X' } })
  fireEvent.click(screen.getByRole('button', { name: 'Create target' }))
  expect(await screen.findByRole('heading', { name: 'Created business' })).toBeInTheDocument()
  expect(screen.getByText('Not ingested')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Ingest reviews' })).toBeEnabled()
})
