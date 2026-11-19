import { useEffect, useId, useRef, type ReactNode } from 'react'

interface ConfirmDialogProps {
  open: boolean
  title: string
  description: string
  confirmLabel: string
  pending: boolean
  pendingLabel?: string
  onConfirm: () => void
  onCancel: () => void
  children?: ReactNode
}

export function ConfirmDialog({ open, title, description, confirmLabel, pending, pendingLabel = 'Deleting...', onConfirm, onCancel, children }: ConfirmDialogProps) {
  const dialog = useRef<HTMLDialogElement>(null)
  const cancel = useRef<HTMLButtonElement>(null)
  const titleId = useId()
  const descriptionId = useId()

  useEffect(() => {
    const element = dialog.current!
    if (open && !element.open) {
      element.showModal()
      cancel.current?.focus()
    } else if (!open && element.open) element.close()
  }, [open])

  return <dialog ref={dialog} className="confirm-dialog" aria-labelledby={titleId}
    aria-describedby={descriptionId} onCancel={(event) => {
      event.preventDefault()
      if (!pending) onCancel()
    }}>
    <h2 id={titleId}>{title}</h2>
    <p id={descriptionId}>{description}</p>
    {children}
    <div className="confirm-dialog-actions">
      <button ref={cancel} type="button" className="button button--secondary" disabled={pending} onClick={onCancel}>Cancel</button>
      <button type="button" className="button button--destructive" disabled={pending} onClick={onConfirm}>
        {pending ? pendingLabel : confirmLabel}
      </button>
    </div>
  </dialog>
}
