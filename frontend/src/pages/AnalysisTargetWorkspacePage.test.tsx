import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { describe, expect, it, vi } from 'vitest'
import App from '../App'
import {
  AnalysisTargetWorkspaceView,
  type AnalysisTargetWorkspaceData,
  type AnalysisTargetWorkspaceState,
} from '../components/workspace/AnalysisTargetWorkspaceView'
import { createFakeAuth, fakeSession } from '../test/fakeAuth'

const config = {
  apiBaseUrl: 'http://api.test',
  supabaseUrl: 'https://test-project.supabase.co',
  supabaseAnonKey: 'sb_publishable_test_key',
}

const targetFixture: AnalysisTargetWorkspaceData = {
  name: 'Example Cafe',
  platform: 'Google Maps',
  sourceReference: 'https://maps.example.test/place/example-cafe',
  latestIngestionState: 'partial',
}

function renderState(state: AnalysisTargetWorkspaceState) {
  return render(
    <MemoryRouter initialEntries={['/targets/example-id']}>
      <AnalysisTargetWorkspaceView state={state} />
    </MemoryRouter>,
  )
}

describe('analysis target workspace route', () => {
  it('requires authentication before showing the workspace', async () => {
    render(
      <MemoryRouter initialEntries={['/targets/example-id']}>
        <App config={config} authClient={createFakeAuth().client} />
      </MemoryRouter>,
    )

    expect(await screen.findByRole('heading', { name: 'Log in' })).toBeInTheDocument()
    expect(screen.queryByText(/target details are unavailable/i)).not.toBeInTheDocument()
  })

  it('shows the honest integration-unavailable state without making an API request', async () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    render(
      <MemoryRouter initialEntries={['/targets/example-id']}>
        <App config={config} authClient={createFakeAuth(fakeSession()).client} />
      </MemoryRouter>,
    )

    expect(await screen.findByRole('heading', { name: 'Target details unavailable' })).toBeInTheDocument()
    expect(screen.getByText(/authorized target-read integration is not available yet/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Ingest reviews' })).toBeDisabled()
    expect(screen.getByText(/S1-019 backend integration/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to dashboard' })).toHaveAttribute('href', '/dashboard')
    expect(fetchMock).not.toHaveBeenCalled()
  })
})

describe('analysis target workspace presentation', () => {
  it('shows loading placeholders', () => {
    const { container } = renderState({ kind: 'loading' })

    expect(container.querySelector('[aria-busy="true"]')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Analysis target workspace' })).toBeInTheDocument()
  })

  it('shows a missing-target state and dashboard path', () => {
    renderState({ kind: 'missing' })

    expect(screen.getByRole('heading', { name: 'Analysis target not found' })).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent('This target could not be found.')
    expect(screen.getByRole('link', { name: 'Back to dashboard' })).toHaveAttribute('href', '/dashboard')
  })

  it('shows a forbidden state without target details', () => {
    renderState({ kind: 'forbidden' })

    expect(screen.getByRole('heading', { name: 'Access denied' })).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent("You don't have access to this analysis target.")
    expect(screen.queryByText(targetFixture.name)).not.toBeInTheDocument()
  })

  it('shows a request error and dashboard path', () => {
    renderState({ kind: 'error', message: 'Please try again.' })

    expect(screen.getByRole('heading', { name: 'Could not load analysis target' })).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent('Please try again.')
    expect(screen.getByRole('link', { name: 'Back to dashboard' })).toHaveAttribute('href', '/dashboard')
  })

  it('displays authorized target details and latest ingestion state', () => {
    renderState({ kind: 'ready', target: targetFixture })

    expect(screen.getByRole('heading', { name: targetFixture.name })).toBeInTheDocument()
    expect(screen.getByText(targetFixture.platform)).toBeInTheDocument()
    expect(screen.getByText(targetFixture.sourceReference)).toBeInTheDocument()
    expect(screen.getByText('Partially ingested')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Ingest reviews' })).toBeDisabled()
  })

  it('uses the not-ingested label when no ingestion state exists', () => {
    renderState({
      kind: 'ready',
      target: { ...targetFixture, latestIngestionState: null },
    })

    expect(screen.getByText('Not ingested')).toBeInTheDocument()
  })

  it('keeps test target data out of the unavailable production state', () => {
    renderState({ kind: 'unavailable' })

    expect(screen.queryByText(targetFixture.name)).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to dashboard' })).toHaveAttribute('href', '/dashboard')
  })

  it('renders the dashboard link as a working route', () => {
    render(
      <MemoryRouter initialEntries={['/targets/example-id']}>
        <Routes>
          <Route
            path="/targets/:targetId"
            element={<AnalysisTargetWorkspaceView state={{ kind: 'missing' }} />}
          />
          <Route path="/dashboard" element={<h1>Dashboard destination</h1>} />
        </Routes>
      </MemoryRouter>,
    )

    fireEvent.click(screen.getByRole('link', { name: 'Back to dashboard' }))
    expect(screen.getByRole('heading', { name: 'Dashboard destination' })).toBeInTheDocument()
  })
})
