import { useId, useState } from 'react'

interface TextFieldProps {
  label: string
  name: string
  value: string
  onChange: (value: string) => void
  type?: 'text' | 'email' | 'password'
  autoComplete?: string
  required?: boolean
  helper?: string
  error?: string
}

export function TextField({
  label,
  name,
  value,
  onChange,
  type = 'text',
  autoComplete,
  required = false,
  helper,
  error,
}: TextFieldProps) {
  const id = useId()
  const [revealed, setRevealed] = useState(false)
  const helperId = helper ? `${id}-helper` : undefined
  const errorId = error ? `${id}-error` : undefined
  const describedBy = [helperId, errorId].filter(Boolean).join(' ') || undefined
  const inputType = type === 'password' && revealed ? 'text' : type

  return (
    <div className="field">
      <label htmlFor={id} className="field__label">
        {label}
        {required && <span aria-hidden="true"> *</span>}
      </label>
      <div className="field__control">
        <input
          id={id}
          name={name}
          type={inputType}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          autoComplete={autoComplete}
          required={required}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          className="field__input"
        />
        {type === 'password' && (
          <button
            type="button"
            className="field__toggle"
            aria-label={revealed ? 'Hide password' : 'Show password'}
            onClick={() => setRevealed((current) => !current)}
          >
            {revealed ? 'Hide' : 'Show'}
          </button>
        )}
      </div>
      {helper && (
        <p id={helperId} className="field__helper">
          {helper}
        </p>
      )}
      {error && (
        <p id={errorId} className="field__error">
          {error}
        </p>
      )}
    </div>
  )
}
