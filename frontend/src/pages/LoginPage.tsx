import { useState, type FormEvent } from 'react'
import { Link, useLocation } from 'react-router'
import { AuthLayout } from '../components/layout/AuthLayout'
import type { RedirectState } from '../components/layout/RouteGuards'
import { Alert } from '../components/ui/Alert'
import { TextField } from '../components/ui/TextField'
import { useAuth } from '../lib/auth/AuthContext'
import { authErrorMessage } from '../lib/auth/authErrors'
import { validateEmail } from '../lib/auth/validation'
import { MESSAGES } from '../lib/messages'

interface FieldErrors {
  email?: string
  password?: string
}

export default function LoginPage() {
  const { signIn } = useAuth()
  const location = useLocation()
  const notice = (location.state as RedirectState | null)?.message
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const [formError, setFormError] = useState<string>()
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const errors: FieldErrors = {
      email: validateEmail(email),
      password: password ? undefined : MESSAGES.passwordRequired,
    }
    setFieldErrors(errors)
    if (errors.email || errors.password) {
      setFormError(MESSAGES.formSummary)
      return
    }

    setFormError(undefined)
    setSubmitting(true)
    try {
      await signIn(email.trim(), password)
    } catch (error) {
      setFormError(authErrorMessage(error))
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout title="Log in">
      {notice && !formError && <Alert variant="info">{notice}</Alert>}
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
          autoComplete="current-password"
          required
          value={password}
          onChange={setPassword}
          error={fieldErrors.password}
        />
        <button type="submit" className="button button--primary" disabled={submitting}>
          {submitting ? 'Logging in...' : 'Log in'}
        </button>
      </form>
      <p className="auth-links">
        Don't have an account? <Link to="/register">Register</Link>
      </p>
    </AuthLayout>
  )
}
