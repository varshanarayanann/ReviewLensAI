import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { Skeleton } from '../ui/Skeleton'
import { AccountMenu } from './AccountMenu'
import { AnalysisSidebar } from './AnalysisSidebar'

export function AppShell({ children, apiBaseUrl }: { children: ReactNode; apiBaseUrl?: string }) {
  return (
    <div className="app-shell">
      <header className="app-header">
        <Link to="/dashboard" className="logo">
          ReviewLens AI
        </Link>
        <AccountMenu />
      </header>
      <div className="app-shell__body">
        {apiBaseUrl ? <AnalysisSidebar apiBaseUrl={apiBaseUrl} /> : null}
        <main className="app-main">{children}</main>
      </div>
    </div>
  )
}

export function AppShellSkeleton() {
  return (
    <div aria-busy="true" aria-label="Loading" className="app-shell">
      <header className="app-header">
        <Skeleton width={120} height={20} />
        <Skeleton width={160} height={20} />
      </header>
      <div className="app-shell__body">
        <aside className="app-sidebar" aria-hidden="true">
          <Skeleton height={20} />
          <Skeleton height={36} />
          <Skeleton height={120} />
        </aside>
        <main className="app-main">
          <Skeleton width={240} height={32} />
          <div className="stack">
            <Skeleton height={96} />
            <Skeleton height={96} />
          </div>
        </main>
      </div>
    </div>
  )
}
