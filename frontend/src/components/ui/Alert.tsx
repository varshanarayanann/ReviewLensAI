import type { ReactNode } from 'react'

type AlertVariant = 'danger' | 'success' | 'info'

export function Alert({ variant, children }: { variant: AlertVariant; children: ReactNode }) {
  return (
    <div role={variant === 'danger' ? 'alert' : 'status'} className={`alert alert--${variant}`}>
      {children}
    </div>
  )
}
