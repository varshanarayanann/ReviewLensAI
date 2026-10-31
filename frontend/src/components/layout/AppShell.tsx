import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { Skeleton } from '../ui/Skeleton'
import { AccountMenu } from './AccountMenu'

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <>
      <header className="app-header">
        <Link to="/dashboard" className="logo">
          ReviewLens AI
        </Link>
        <AccountMenu />
      </header>
      <main className="app-main">{children}</main>
    </>
  )
}

export function AppShellSkeleton() {
  return (
    <div aria-busy="true" aria-label="Loading">
      <header className="app-header">
        <Skeleton width={120} height={20} />
        <Skeleton width={160} height={20} />
      </header>
      <main className="app-main">
        <Skeleton width={240} height={32} />
        <div className="stack">
          <Skeleton height={96} />
          <Skeleton height={96} />
        </div>
      </main>
    </div>
  )
}
