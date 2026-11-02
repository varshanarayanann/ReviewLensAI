import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { MESSAGES } from '../../lib/messages'
import { Alert } from '../ui/Alert'
import { Skeleton } from '../ui/Skeleton'

export type IngestionState = 'processing' | 'succeeded' | 'partial' | 'failed'

export interface AnalysisTargetWorkspaceData {
  name: string
  platform: string
  sourceReference: string
  latestIngestionState?: IngestionState | null
}

export type AnalysisTargetWorkspaceState =
  | { kind: 'loading' }
  | { kind: 'missing' }
  | { kind: 'forbidden' }
  | { kind: 'error'; message: string }
  | { kind: 'ready'; target: AnalysisTargetWorkspaceData }

const ingestionLabels: Record<IngestionState | 'not-ingested', string> = {
  processing: 'Ingesting', succeeded: 'Ingested', partial: 'Partially ingested',
  failed: 'Failed', 'not-ingested': 'Not ingested',
}

export function AnalysisTargetWorkspaceView({ state, children }: {
  state: AnalysisTargetWorkspaceState
  children?: ReactNode
}) {
  if (state.kind === 'loading') return (
    <section className="workspace-content" aria-busy="true" aria-label="Loading workspace">
      <h1>Analysis workspace</h1>
      <div className="stack"><Skeleton width="100%" height={24} /><Skeleton height={72} /></div>
    </section>
  )

  if (state.kind === 'ready') {
    const status = state.target.latestIngestionState ?? 'not-ingested'
    return (
      <section className="workspace-content">
        <h1>{state.target.name}</h1>
        <dl className="workspace-details">
          <div><dt>Review platform</dt><dd>{state.target.platform}</dd></div>
          <div><dt>Source reference</dt><dd className="workspace-source">
            <a href={state.target.sourceReference} target="_blank" rel="noopener noreferrer"
              title={state.target.sourceReference}>{state.target.sourceReference}</a>
          </dd></div>
          <div><dt>Ingestion status</dt><dd>
            <span className={`workspace-status workspace-status--${status}`}>{ingestionLabels[status]}</span>
          </dd></div>
        </dl>
        {children}
        <Link to="/dashboard">Back to dashboard</Link>
      </section>
    )
  }

  return (
    <section className="workspace-content">
      <h1>{state.kind === 'error' ? 'Could not load analysis target' : 'Analysis target not found'}</h1>
      <Alert variant="danger">{state.kind === 'error' ? state.message : MESSAGES.targetNotFound}</Alert>
      <Link to="/dashboard" className="button button--secondary workspace-dashboard-link">Back to dashboard</Link>
    </section>
  )
}
