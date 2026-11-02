import type { ReactNode } from 'react'

export function EmptyState({ title, description, action }: {
  title: string
  description: string
  action?: ReactNode
}) {
  return <div className="empty-state">
    <h2>{title}</h2>
    <p className="muted">{description}</p>
    {action}
  </div>
}
