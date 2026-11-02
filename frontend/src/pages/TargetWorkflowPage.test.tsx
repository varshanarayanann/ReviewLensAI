import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { expect, it, vi } from 'vitest'
import App from '../App'
import { createFakeAuth, fakeSession } from '../test/fakeAuth'
import { MESSAGES } from '../lib/messages'

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

it('maps rejected CSV sources to import guidance and retains the selected file', async () => {
  vi.stubGlobal('fetch', vi.fn((url: string, options?: RequestInit) => Promise.resolve(new Response(JSON.stringify(
    options?.method === 'POST' ? { detail: 'private parser detail' }
      : url.endsWith('/latest') ? null : { name: 'Import target', source_url: 'https://google.com/maps/place/X' },
  ), { status: options?.method === 'POST' ? 422 : 200 }))))
  render(<MemoryRouter initialEntries={['/targets/target-id']}><App config={config} authClient={createFakeAuth(fakeSession()).client} /></MemoryRouter>)
  await screen.findByRole('heading', { name: 'Import target' })
  const file = new File(['rating,text\n5,Review'], 'reviews.csv', { type: 'text/csv' })
  Object.defineProperty(file, 'text', { value: () => Promise.resolve('rating,text\n5,Review') })
  fireEvent.change(screen.getByLabelText('CSV file *'), { target: { files: [file] } })
  fireEvent.submit(screen.getByRole('button', { name: 'Upload reviews' }).closest('form')!)
  expect(await screen.findByRole('alert')).toHaveTextContent(MESSAGES.csvSourceInvalid)
  expect(screen.queryByText('private parser detail')).not.toBeInTheDocument()
  expect(screen.getByLabelText('CSV file *')).toHaveProperty('files', [file])
})
