import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { expect, it, vi } from 'vitest'
import App from '../App'
import { createFakeAuth, fakeSession } from '../test/fakeAuth'

const config = { apiBaseUrl: 'http://api.test', supabaseUrl: 'https://auth.test', supabaseAnonKey: 'public' }
const targetsUrl = `${config.apiBaseUrl}/api/targets`
const phone = {
  id: 'phone', name: 'Phone store', platform: 'google_maps',
  source_url: 'https://google.com/maps/place/Phone', created_at: '2026-11-01T00:00:00Z',
}
const service = {
  id: 'service', name: 'Call center', platform: 'google_maps',
  source_url: 'https://google.com/maps/place/Service', created_at: '2026-11-01T00:00:00Z',
}
const datasets = [
  { target: phone, count: 3, rating: 4, answer: 'Reviewers mention long battery life.' },
  { target: service, count: 2, rating: 2, answer: 'Reviewers mention slow customer service.' },
]
const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status })

it('asks the same question against the newly active target and shows its matching summary', async () => {
  const fetchMock = vi.fn((url: string, options?: RequestInit) => {
    if (url === targetsUrl) return Promise.resolve(json([phone, service]))
    for (const { target, count, rating, answer } of datasets) {
      const path = `${targetsUrl}/${target.id}`
      if (url === path) return Promise.resolve(json(target))
      if (url === `${path}/ingestions/latest`) return Promise.resolve(json(null))
      if (url === `${path}/reviews/summary`) {
        return Promise.resolve(json({ target_id: target.id, review_count: count, average_rating: rating }))
      }
      if (url === `${path}/questions` && options?.method === 'POST') {
        return Promise.resolve(json({ target_id: target.id, status: 'answered', answer, review_count: count }))
      }
    }
    return Promise.resolve(json({}, 404))
  })
  vi.stubGlobal('fetch', fetchMock)

  render(<MemoryRouter initialEntries={['/targets/phone']}>
    <App config={config} authClient={createFakeAuth(fakeSession()).client} />
  </MemoryRouter>)

  const question = 'What themes do reviewers mention?'
  async function ask() {
    const input = await screen.findByRole('textbox', { name: 'Question *' })
    expect(input).toHaveValue('')
    fireEvent.change(input, { target: { value: question } })
    fireEvent.click(screen.getByRole('button', { name: 'Ask question' }))
  }

  expect(await screen.findByRole('heading', { level: 1, name: phone.name })).toBeInTheDocument()
  expect(await screen.findByText('3 reviews')).toBeInTheDocument()
  await ask()
  expect(await screen.findByText(datasets[0].answer)).toBeInTheDocument()

  fireEvent.click(screen.getByRole('link', { name: 'Back to dashboard' }))
  fireEvent.click(await screen.findByRole('link', { name: 'Open Call center' }))

  expect(await screen.findByRole('heading', { level: 1, name: service.name })).toBeInTheDocument()
  expect(screen.getByRole('link', { name: service.source_url })).toBeInTheDocument()
  expect(await screen.findByText('2 reviews')).toBeInTheDocument()
  expect(screen.getByText('2.0 / 5')).toBeInTheDocument()
  expect(screen.queryByText('3 reviews')).not.toBeInTheDocument()
  expect(screen.queryByText(datasets[0].answer)).not.toBeInTheDocument()
  await ask()
  expect(await screen.findByText(datasets[1].answer)).toBeInTheDocument()

  expect(fetchMock.mock.calls.filter(([, options]) => options?.method === 'POST')).toEqual(
    datasets.map(({ target }) => [
      `${targetsUrl}/${target.id}/questions`,
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({ Authorization: 'Bearer test-access-token' }),
        body: JSON.stringify({ question }),
      }),
    ]),
  )
})
