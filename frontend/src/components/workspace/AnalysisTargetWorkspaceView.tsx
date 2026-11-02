import { Link } from 'react-router'
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
  | { kind: 'unavailable' }
  | { kind: 'missing' }
  | { kind: 'forbidden' }
  | { kind: 'error'; message: string }
  | { kind: 'ready'; target: AnalysisTargetWorkspaceData }

const ingestionLabels: Record<IngestionState | 'not-ingested', string> = {
  processing: 'Ingesting',
  succeeded: 'Ingested',
  partial: 'Partially ingested',
  failed: 'Failed',
  'not-ingested': 'Not ingested',
}

export function AnalysisTargetWorkspaceView({
  state,
}: {
  state: AnalysisTargetWorkspaceState
}) {
  if (state.kind === 'loading') {
    return (
      <section className="workspace-content" aria-busy="true">
        <h1>Analysis target workspace</h1>
        <div className="stack">
          <Skeleton width={280} height={24} />
          <Skeleton height={72} />
          <Skeleton width={180} height={36} />
        </div>
      </section>
    )
  }

  if (state.kind === 'ready') {
    const ingestionState = state.target.latestIngestionState ?? 'not-ingested'

    return (
      <section className="workspace-content">
        <h1>{state.target.name}</h1>
        <dl className="workspace-details">
          <div>
            <dt>Review platform</dt>
            <dd>{state.target.platform}</dd>
          </div>
          <div>
            <dt>Source reference</dt>
            <dd className="workspace-source">{state.target.sourceReference}</dd>
          </div>
          <div>
            <dt>Ingestion status</dt>
            <dd>
              <span className={`workspace-status workspace-status--${ingestionState}`}>
                {ingestionLabels[ingestionState]}
              </span>
            </dd>
          </div>
        </dl>
        <section className="workspace-ingestion">
          <h2>Reviews</h2>
          <button className="button button--primary" type="button" disabled>
            Ingest reviews
          </button>
          <p className="muted">
            Ingestion is unavailable until the S1-019 backend integration is implemented.
          </p>
        </section>
      </section>
    )
  }

  const content = {
    unavailable: {
      title: 'Target details unavailable',
      description:
        'The authorized target-read integration is not available yet. No target details have been loaded.',
      variant: 'info' as const,
    },
    missing: {
      title: 'Analysis target not found',
      description: 'This target could not be found.',
      variant: 'danger' as const,
    },
    forbidden: {
      title: 'Access denied',
      description: "You don't have access to this analysis target.",
      variant: 'danger' as const,
    },
    error: {
      title: 'Could not load analysis target',
      description: '',
      variant: 'danger' as const,
    },
  }[state.kind]
  const description = state.kind === 'error' ? state.message : content.description

  return (
    <section className="workspace-content">
      <h1>{content.title}</h1>
      <Alert variant={content.variant}>{description}</Alert>
      {state.kind === 'unavailable' && (
        <section className="workspace-ingestion">
          <h2>Reviews</h2>
          <button className="button button--primary" type="button" disabled>
            Ingest reviews
          </button>
          <p className="muted">
            Ingestion is unavailable until the S1-019 backend integration is implemented.
          </p>
        </section>
      )}
      <Link to="/dashboard" className="button button--secondary workspace-dashboard-link">
        Back to dashboard
      </Link>
    </section>
  )
}
