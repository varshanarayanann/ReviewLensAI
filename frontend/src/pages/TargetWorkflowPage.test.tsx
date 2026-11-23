import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { expect, it, vi } from 'vitest'
import App from '../App'
import { createFakeAuth, fakeSession } from '../test/fakeAuth'

const config = { apiBaseUrl: 'http://api.test', supabaseUrl: 'http://auth.test', supabaseAnonKey: 'public' }

function stubFetch(handler: (url: string, options?: RequestInit) => unknown) {
  vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL, options?: RequestInit) => {
    const url = String(input)
    if (url.includes('/questions?') && options?.method === 'GET') {
      return Promise.resolve(new Response('[]', { status: 200 }))
    }
    if (url.endsWith('/api/targets') && options?.method !== 'POST' && options?.method !== 'PATCH') {
      return Promise.resolve(new Response(JSON.stringify([])))
    }
    const body = handler(url, options)
    if (body instanceof Response) return Promise.resolve(body)
    return Promise.resolve(new Response(JSON.stringify(body)))
  }))
}

it('maps backend validation failures and preserves input', async () => {
  stubFetch(() => new Response('{}', { status: 422 }))
  render(<MemoryRouter initialEntries={['/targets/new']}><App config={config} authClient={createFakeAuth(fakeSession()).client} /></MemoryRouter>)
  await screen.findByRole('heading', { name: 'Create target' })
  fireEvent.change(screen.getByLabelText('Analysis name *'), { target: { value: 'Example' } })
  fireEvent.change(screen.getByLabelText('Google Maps URL *'), { target: { value: 'https://bad.example/' } })
  fireEvent.click(screen.getByRole('button', { name: 'Save analysis' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('valid HTTPS Google Maps')
  expect(screen.getByLabelText('Analysis name *')).toHaveValue('Example')
})

it('restores a recorded failed ingestion with target context', async () => {
  stubFetch((url) => (
    url.endsWith('/latest') ? { state: 'failed', persisted_count: 0, message: 'Reviews could not be collected. Try again shortly.' }
      : url.endsWith('/reviews/summary')
        ? { target_id: 'target-id', review_count: 0, average_rating: null }
        : { id: 'target-id', name: 'Example business', platform: 'google_maps', source_url: 'https://google.com/maps/place/X' }
  ))
  render(<MemoryRouter initialEntries={['/targets/target-id']}><App config={config} authClient={createFakeAuth(fakeSession()).client} /></MemoryRouter>)
  expect(await screen.findByRole('alert')).toHaveTextContent('Try again')
  expect(await screen.findByRole('heading', { name: 'Example business' })).toBeInTheDocument()
})

it('opens the workspace for a newly created target', async () => {
  stubFetch((url, options) => (
    options?.method === 'POST' ? { id: 'created-target' } : url.endsWith('/latest') ? null
      : url.endsWith('/reviews/summary')
        ? { target_id: 'created-target', review_count: 0, average_rating: null }
        : { id: 'created-target', name: 'Created business', platform: 'google_maps', source_url: 'https://google.com/maps/place/X' }
  ))
  render(<MemoryRouter initialEntries={['/targets/new']}><App config={config} authClient={createFakeAuth(fakeSession()).client} /></MemoryRouter>)
  await screen.findByRole('heading', { name: 'Create target' })
  fireEvent.change(screen.getByLabelText('Analysis name *'), { target: { value: 'Created business' } })
  fireEvent.change(screen.getByLabelText('Google Maps URL *'), { target: { value: 'https://google.com/maps/place/X' } })
  fireEvent.click(screen.getByRole('button', { name: 'Save analysis' }))
  expect(await screen.findByRole('heading', { name: 'Created business' })).toBeInTheDocument()
  expect(screen.getByText('Not ingested')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Ingest reviews' })).toBeEnabled()
})

it('suggests a short name from the Google Maps place URL', async () => {
  stubFetch(() => [])
  render(<MemoryRouter initialEntries={['/targets/new']}><App config={config} authClient={createFakeAuth(fakeSession()).client} /></MemoryRouter>)
  await screen.findByRole('heading', { name: 'Create target' })
  fireEvent.change(screen.getByLabelText('Google Maps URL *'), {
    target: { value: 'https://www.google.com/maps/place/Hapive+Coffee/@40.7,-74.1' },
  })
  expect(screen.getByLabelText('Analysis name *')).toHaveValue('Hapive Coffee')
})
