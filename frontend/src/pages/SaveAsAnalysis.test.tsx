import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, expect, it } from 'vitest'
import App from '../App'
import { suggestCopyAnalysisName } from '../lib/api/client'
import { createFakeAuth, fakeSession } from '../test/fakeAuth'
import { stubFetchWithEmptyHistory } from '../test/emptyHistory'

const config = { apiBaseUrl: 'http://api.test', supabaseUrl: 'https://auth.test', supabaseAnonKey: 'public' }
const source = {
  id: 'target-a',
  name: 'Hapive Coffee',
  platform: 'google_maps' as const,
  source_url: 'https://www.google.com/maps/place/Hapive+Coffee',
  created_at: '2026-01-01T12:00:00Z',
}
const copy = {
  id: 'target-copy',
  name: 'Hapive Coffee copy',
  platform: 'google_maps' as const,
  source_url: source.source_url,
  created_at: '2026-01-02T12:00:00Z',
}
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status })
let fetchMock: ReturnType<typeof stubFetchWithEmptyHistory>
let listed = [source]

beforeEach(() => {
  listed = [source]
  fetchMock = stubFetchWithEmptyHistory((url: string, options?: RequestInit) => {
    if (typeof url === 'string' && url.endsWith('/copies') && options?.method === 'POST') {
      listed = [source, copy]
      return Promise.resolve(json({
        id: copy.id,
        name: copy.name,
        platform: 'google_maps',
        source_url: copy.source_url,
      }, 201))
    }
    if (typeof url === 'string' && url.endsWith('/api/targets')) {
      return Promise.resolve(json(listed))
    }
    if (typeof url === 'string' && url.endsWith('/latest')) return Promise.resolve(json(null))
    if (typeof url === 'string' && url.includes('/reviews/summary')) {
      const id = url.includes(copy.id) ? copy.id : source.id
      return Promise.resolve(json({ target_id: id, review_count: 0, average_rating: null }))
    }
    if (typeof url === 'string' && url.includes(`/targets/${copy.id}`)) {
      return Promise.resolve(json({
        id: copy.id,
        name: copy.name,
        platform: 'google_maps',
        source_url: copy.source_url,
      }))
    }
    return Promise.resolve(json({
      id: source.id,
      name: source.name,
      platform: 'google_maps',
      source_url: source.source_url,
    }))
  })
})

it('saves a named copy and opens the new analysis workspace', async () => {
  render(<MemoryRouter initialEntries={['/targets/target-a']}>
    <App config={config} authClient={createFakeAuth(fakeSession()).client} />
  </MemoryRouter>)
  expect(await screen.findByRole('heading', { name: 'Hapive Coffee' })).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Save as new analysis' }))
  const nameField = screen.getByLabelText('New analysis name *')
  expect(nameField).toHaveValue('Hapive Coffee copy')
  fireEvent.click(screen.getByRole('button', { name: 'Save as' }))
  expect(await screen.findByRole('heading', { name: 'Hapive Coffee copy' })).toBeInTheDocument()
  await waitFor(() => {
    expect(fetchMock).toHaveBeenCalledWith(
      'http://api.test/api/targets/target-a/copies',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ name: 'Hapive Coffee copy' }),
      }),
    )
  })
  expect(screen.getByRole('link', { name: source.source_url })).toHaveAttribute('href', source.source_url)
  const nav = screen.getByRole('navigation', { name: 'Analysis navigation' })
  expect(within(nav).getByRole('link', { name: /Hapive Coffee copy/i })).toHaveAttribute(
    'href',
    '/targets/target-copy',
  )
})

it('suggests a truncated Save As name within 120 characters', () => {
  expect(suggestCopyAnalysisName('Hapive')).toBe('Hapive copy')
  const long = 'x'.repeat(120)
  expect(suggestCopyAnalysisName(long)).toHaveLength(120)
  expect(suggestCopyAnalysisName(long).endsWith(' copy')).toBe(true)
})
