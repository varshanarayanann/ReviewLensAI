import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, expect, it } from 'vitest'
import App from '../App'
import { suggestAnalysisName } from '../lib/api/client'
import { createFakeAuth, fakeSession } from '../test/fakeAuth'
import { stubFetchWithEmptyHistory } from '../test/emptyHistory'

const config = { apiBaseUrl: 'http://api.test', supabaseUrl: 'https://auth.test', supabaseAnonKey: 'public' }
const target = {
  id: 'target-a',
  name: 'Hapive Coffee',
  platform: 'google_maps' as const,
  source_url: 'https://www.google.com/maps/place/Hapive+Coffee',
  created_at: '2026-01-01T12:00:00Z',
}
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status })
let fetchMock: ReturnType<typeof stubFetchWithEmptyHistory>

beforeEach(() => {
  fetchMock = stubFetchWithEmptyHistory((url: string, options?: RequestInit) => {
    if (options?.method === 'PATCH') {
      return Promise.resolve(json({
        id: target.id,
        name: 'Downtown Hapive',
        platform: 'google_maps',
        source_url: target.source_url,
      }))
    }
    if (typeof url === 'string' && url.endsWith('/api/targets')) {
      return Promise.resolve(json([target]))
    }
    if (typeof url === 'string' && url.endsWith('/latest')) return Promise.resolve(json(null))
    if (typeof url === 'string' && url.endsWith('/reviews/summary')) {
      return Promise.resolve(json({ target_id: target.id, review_count: 0, average_rating: null }))
    }
    return Promise.resolve(json({
      id: target.id,
      name: target.name,
      platform: 'google_maps',
      source_url: target.source_url,
    }))
  })
})

it('lists saved analysis names in the sidebar', async () => {
  render(<MemoryRouter initialEntries={['/dashboard']}>
    <App config={config} authClient={createFakeAuth(fakeSession()).client} />
  </MemoryRouter>)
  expect(await screen.findByRole('navigation', { name: 'Analysis navigation' })).toBeInTheDocument()
  expect(await screen.findByRole('heading', { name: 'Saved analyses' })).toBeInTheDocument()
  const analysisLinks = await screen.findAllByRole('link', { name: /Hapive Coffee/i })
  expect(analysisLinks.some((link) => link.getAttribute('href') === '/targets/target-a')).toBe(true)
})

it('renames an analysis without changing the source URL', async () => {
  render(<MemoryRouter initialEntries={['/targets/target-a']}>
    <App config={config} authClient={createFakeAuth(fakeSession()).client} />
  </MemoryRouter>)
  expect(await screen.findByRole('heading', { name: 'Hapive Coffee' })).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Rename analysis' }))
  fireEvent.change(screen.getByLabelText('Analysis name *'), { target: { value: 'Downtown Hapive' } })
  fireEvent.click(screen.getByRole('button', { name: 'Save name' }))
  expect(await screen.findByRole('heading', { name: 'Downtown Hapive' })).toBeInTheDocument()
  await waitFor(() => {
    expect(fetchMock).toHaveBeenCalledWith(
      'http://api.test/api/targets/target-a',
      expect.objectContaining({
        method: 'PATCH',
        body: JSON.stringify({ name: 'Downtown Hapive' }),
      }),
    )
  })
  expect(screen.getByRole('link', { name: target.source_url })).toHaveAttribute('href', target.source_url)
})

it('suggests an analysis name from a Google Maps place URL', () => {
  expect(suggestAnalysisName('https://www.google.com/maps/place/Hapive+Coffee/@40.7,-74.1'))
    .toBe('Hapive Coffee')
  expect(suggestAnalysisName('https://maps.app.goo.gl/abc')).toBe('')
})
