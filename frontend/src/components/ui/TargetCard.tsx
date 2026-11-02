import { Link } from 'react-router'
import type { AnalysisTargetResponse } from '../../lib/api/client'
import { PlatformBadge } from './PlatformBadge'

export function TargetCard({ target }: { target: AnalysisTargetResponse }) {
  return (
    <Link to={`/targets/${target.id}`} className="target-card" aria-label={`Open ${target.name}`}>
      <h2>{target.name}</h2>
      <PlatformBadge />
      <span className="target-card__source muted" title={target.source_url}>{target.source_url}</span>
      <span className="muted">Created <time dateTime={target.created_at}>
        {new Date(target.created_at).toLocaleDateString('en-US', {
          month: 'short', day: 'numeric', year: 'numeric',
        })}
      </time></span>
    </Link>
  )
}
