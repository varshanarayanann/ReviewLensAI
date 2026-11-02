import type { ReactNode } from 'react'

export function AuthLayout({ title, children }: { title: string; children: ReactNode }) {
  return (
    <main className="auth-layout">
      <p className="logo">ReviewLens AI</p>
      <section className="auth-card" aria-labelledby="auth-title">
        <h1 id="auth-title">{title}</h1>
        {children}
      </section>
    </main>
  )
}
