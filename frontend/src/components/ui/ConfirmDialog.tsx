import { useEffect, useRef, type ReactNode } from 'react'

interface ConfirmDialogProps {
  open: boolean
  title: string
  description: string
  confirmLabel: string
  pending: boolean
  onConfirm: () => void
  onCancel: () => void
  children?: ReactNode
}

export function ConfirmDialog({ open, title, description, confirmLabel, pending, onConfirm, onCancel, children }: ConfirmDialogProps) {
  const dialog = useRef<HTMLDialogElement>(null)
  const cancel = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    const element = dialog.current!
    if (open && !element.open) {
      element.showModal()
      cancel.current?.focus()
    } else if (!open && element.open) element.close()
  }, [open])

  return <dialog ref={dialog} className="confirm-dialog" aria-labelledby="confirm-dialog-title"
    aria-describedby="confirm-dialog-description" onCancel={(event) => {
      event.preventDefault()
      if (!pending) onCancel()
    }}>
    <h2 id="confirm-dialog-title">{title}</h2>
    <p id="confirm-dialog-description">{description}</p>
    {children}
    <div className="confirm-dialog-actions">
      <button ref={cancel} type="button" className="button button--secondary" disabled={pending} onClick={onCancel}>Cancel</button>
      <button type="button" className="button button--destructive" disabled={pending} onClick={onConfirm}>
        {pending ? 'Deleting...' : confirmLabel}
      </button>
    </div>
  </dialog>
}
