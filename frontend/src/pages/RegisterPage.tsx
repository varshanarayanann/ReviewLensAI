import { useState, type FormEvent } from 'react'
import { Link } from 'react-router'
import { AuthLayout } from '../components/layout/AuthLayout'
import { Alert } from '../components/ui/Alert'
import { TextField } from '../components/ui/TextField'
import { useAuth } from '../lib/auth/AuthContext'
import { authErrorMessage } from '../lib/auth/authErrors'
import { MIN_PASSWORD_LENGTH, validateEmail, validateNewPassword } from '../lib/auth/validation'
import { MESSAGES } from '../lib/messages'

interface FieldErrors {
  email?: string
  password?: string
  confirmPassword?: string
}

export default function RegisterPage() {
  const { signUp } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const [formError, setFormError] = useState<string>()
  const [confirmationSent, setConfirmationSent] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const errors: FieldErrors = {
      email: validateEmail(email),
      password: validateNewPassword(password),
      confirmPassword: confirmPassword === password ? undefined : MESSAGES.passwordsDontMatch,
    }
    setFieldErrors(errors)
    if (errors.email || errors.password || errors.confirmPassword) {
      setFormError(MESSAGES.formSummary)
      return
    }

    setFormError(undefined)
    setSubmitting(true)
    try {
      const result = await signUp(email.trim(), password)
      if (result === 'email_exists') setFormError(MESSAGES.emailExists)
      if (result === 'confirmation_required') setConfirmationSent(true)
    } catch (error) {
      setFormError(authErrorMessage(error))
    }
    setSubmitting(false)
  }

  if (confirmationSent) {
    return (
      <AuthLayout title="Check your email">
        <Alert variant="success">{MESSAGES.confirmationSent}</Alert>
        <p className="auth-links">
          <Link to="/login">Back to log in</Link>
        </p>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout title="Register">
      {formError && <Alert variant="danger">{formError}</Alert>}
      <form className="form" onSubmit={handleSubmit} noValidate>
        <p className="muted">* Required</p>
        <TextField
          label="Email"
          name="email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={setEmail}
          error={fieldErrors.email}
        />
        <TextField
          label="Password"
          name="password"
          type="password"
          autoComplete="new-password"
          required
          helper={`At least ${MIN_PASSWORD_LENGTH} characters.`}
          value={password}
          onChange={setPassword}
          error={fieldErrors.password}
        />
        <TextField
          label="Confirm password"
          name="confirmPassword"
          type="password"
          autoComplete="new-password"
          required
          value={confirmPassword}
          onChange={setConfirmPassword}
          error={fieldErrors.confirmPassword}
        />
        <button type="submit" className="button button--primary" disabled={submitting}>
          {submitting ? 'Creating account...' : 'Create account'}
        </button>
      </form>
      <p className="auth-links">
        Already have an account? <Link to="/login">Log in</Link>
      </p>
    </AuthLayout>
  )
}
