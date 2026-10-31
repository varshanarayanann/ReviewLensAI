import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import App from './App'

const config = { apiBaseUrl: 'http://api.test' }

describe('App', () => {
  it('shows connected when the backend health check succeeds', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: 'ok' }), { status: 200 }),
    )
    vi.stubGlobal('fetch', fetchMock)

    render(<App config={config} />)

    expect(await screen.findByText('Backend connected')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith('http://api.test/api/health')
  })

  it('shows an actionable message when the backend is unreachable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    render(<App config={config} />)

    expect(await screen.findByText(/Can't reach the backend/)).toBeInTheDocument()
    expect(screen.queryByText(/Failed to fetch/)).not.toBeInTheDocument()
  })
})
