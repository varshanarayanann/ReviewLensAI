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
      : { name: 'Example business', source_url: 'https://google.com/maps/place/X' },
  )))))
  render(<MemoryRouter initialEntries={['/targets/target-id']}><App config={config} authClient={createFakeAuth(fakeSession()).client} /></MemoryRouter>)
  expect(await screen.findByRole('alert')).toHaveTextContent('Try again')
  expect(await screen.findByRole('heading', { name: 'Example business' })).toBeInTheDocument()
})
