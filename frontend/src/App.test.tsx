import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { AuthApiError, AuthRetryableFetchError } from '@supabase/supabase-js'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { MESSAGES } from './lib/messages'
import { createFakeAuth, fakeSession } from './test/fakeAuth'

const config = {
  apiBaseUrl: 'http://api.test',
  supabaseUrl: 'https://test-project.supabase.co',
  supabaseAnonKey: 'sb_publishable_test_key',
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

function renderApp(path: string, fake = createFakeAuth()) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <App config={config} authClient={fake.client} />
    </MemoryRouter>,
  )
  return fake
}

function fillIn(label: RegExp, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } })
}

let fetchMock: ReturnType<typeof vi.fn>

beforeEach(() => {
  fetchMock = vi.fn().mockResolvedValue(jsonResponse({ id: 'user-a-id', email: 'user.a@example.com' }))
  vi.stubGlobal('fetch', fetchMock)
})

describe('route protection', () => {
  it('redirects a logged-out visit to /dashboard to the login page', async () => {
    renderApp('/dashboard')

    expect(await screen.findByRole('heading', { name: 'Log in' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Dashboard' })).not.toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('shows a loading skeleton, not protected content, while the session is restored', () => {
    const fake = createFakeAuth()
    fake.auth.getSession.mockReturnValue(new Promise(() => {}))

    renderApp('/dashboard', fake)

    expect(screen.getByLabelText('Loading')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Dashboard' })).not.toBeInTheDocument()
  })

  it('sends / to the login page when logged out', async () => {
    renderApp('/')

    expect(await screen.findByRole('heading', { name: 'Log in' })).toBeInTheDocument()
  })

  it('sends / to the dashboard when logged in', async () => {
    renderApp('/', createFakeAuth(fakeSession()))

    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
  })

  it('sends a logged-in user away from /login to the dashboard', async () => {
    renderApp('/login', createFakeAuth(fakeSession()))

    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
  })

  it('shows a not found page for unknown routes', () => {
    renderApp('/does-not-exist')

    expect(screen.getByRole('heading', { name: 'Page not found' })).toBeInTheDocument()
  })
})

describe('log in', () => {
  it('logs in and returns the user to the page they originally requested', async () => {
    const fake = renderApp('/dashboard')
    fake.auth.signInWithPassword.mockResolvedValue({ data: { session: fakeSession() }, error: null })

    await screen.findByRole('heading', { name: 'Log in' })
    fillIn(/^Email/, ' user.a@example.com ')
    fillIn(/^Password/, 'correct-password')
    fireEvent.click(screen.getByRole('button', { name: 'Log in' }))

    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
    expect(fake.auth.signInWithPassword).toHaveBeenCalledWith({
      email: 'user.a@example.com',
      password: 'correct-password',
    })
    expect(await screen.findByText('Logged in as user.a@example.com')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith('http://api.test/api/me', {
      headers: { Authorization: 'Bearer test-access-token' },
    })
  })

  it('shows the mapped message for wrong credentials, never the Supabase text', async () => {
    const fake = renderApp('/login')
    fake.auth.signInWithPassword.mockResolvedValue({
      data: { session: null, user: null },
      error: new AuthApiError('Invalid login credentials', 400, 'invalid_credentials'),
    })

    await screen.findByRole('heading', { name: 'Log in' })
    fillIn(/^Email/, 'user.a@example.com')
    fillIn(/^Password/, 'wrong-password')
    fireEvent.click(screen.getByRole('button', { name: 'Log in' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(MESSAGES.invalidCredentials)
    expect(screen.queryByText(/Invalid login credentials/)).not.toBeInTheDocument()
    expect(screen.getByLabelText(/^Email/)).toHaveValue('user.a@example.com')
  })

  it.each([
    [new AuthApiError('Email not confirmed', 400, 'email_not_confirmed'), MESSAGES.emailNotConfirmed],
    [new AuthApiError('Request rate limit reached', 429, 'over_request_rate_limit'), MESSAGES.tooManyAttempts],
    [new AuthRetryableFetchError('Failed to fetch', 0), MESSAGES.offline],
  ])('maps %s to a user-facing message', async (error, message) => {
    const fake = renderApp('/login')
    fake.auth.signInWithPassword.mockResolvedValue({ data: { session: null, user: null }, error })

    await screen.findByRole('heading', { name: 'Log in' })
    fillIn(/^Email/, 'user.a@example.com')
    fillIn(/^Password/, 'any-password')
    fireEvent.click(screen.getByRole('button', { name: 'Log in' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(message)
  })

  it('validates required fields before calling Supabase', async () => {
    const fake = renderApp('/login')

    await screen.findByRole('heading', { name: 'Log in' })
    fireEvent.click(screen.getByRole('button', { name: 'Log in' }))

    expect(screen.getByRole('alert')).toHaveTextContent(MESSAGES.formSummary)
    expect(screen.getByText(MESSAGES.emailRequired)).toBeInTheDocument()
    expect(screen.getByText(MESSAGES.passwordRequired)).toBeInTheDocument()
    expect(screen.getByLabelText(/^Email/)).toHaveAttribute('aria-invalid', 'true')
    expect(fake.auth.signInWithPassword).not.toHaveBeenCalled()
  })

  it('lets the user show and hide the password', async () => {
    renderApp('/login')

    await screen.findByRole('heading', { name: 'Log in' })
    const password = screen.getByLabelText(/^Password/)
    expect(password).toHaveAttribute('type', 'password')

    fireEvent.click(screen.getByRole('button', { name: 'Show password' }))
    expect(password).toHaveAttribute('type', 'text')
  })
})

describe('register', () => {
  async function submitRegistration(email: string, password: string, confirm = password) {
    await screen.findByRole('heading', { name: 'Register' })
    fillIn(/^Email/, email)
    fillIn(/^Password/, password)
    fillIn(/^Confirm password/, confirm)
    fireEvent.click(screen.getByRole('button', { name: 'Create account' }))
  }

  it('tells the user to confirm their email when Supabase requires it', async () => {
    const fake = renderApp('/register')
    fake.auth.signUp.mockResolvedValue({
      data: { session: null, user: { id: 'new-user', identities: [{ id: 'identity' }] } },
      error: null,
    })

    await submitRegistration('new.user@example.com', 'long-enough-password')

    expect(await screen.findByText(MESSAGES.confirmationSent)).toBeInTheDocument()
    expect(fake.auth.signUp).toHaveBeenCalledWith(
      expect.objectContaining({ email: 'new.user@example.com', password: 'long-enough-password' }),
    )
  })

  it('goes straight to the dashboard when Supabase returns a session', async () => {
    const fake = renderApp('/register')
    fake.auth.signUp.mockResolvedValue({ data: { session: fakeSession(), user: fakeSession().user }, error: null })

    await submitRegistration('user.a@example.com', 'long-enough-password')

    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
  })

  it('reports an existing account without revealing Supabase details', async () => {
    const fake = renderApp('/register')
    fake.auth.signUp.mockResolvedValue({
      data: { session: null, user: { id: 'obfuscated', identities: [] } },
      error: null,
    })

    await submitRegistration('user.a@example.com', 'long-enough-password')

    expect(await screen.findByRole('alert')).toHaveTextContent(MESSAGES.emailExists)
  })

  it('rejects short and mismatched passwords before calling Supabase', async () => {
    const fake = renderApp('/register')

    await submitRegistration('user.a@example.com', 'short', 'different')

    expect(screen.getByText(MESSAGES.passwordTooShort)).toBeInTheDocument()
    expect(screen.getByText(MESSAGES.passwordsDontMatch)).toBeInTheDocument()
    expect(fake.auth.signUp).not.toHaveBeenCalled()
  })
})

describe('session', () => {
  it('shows the account email and logs out to the login page', async () => {
    const fake = renderApp('/dashboard', createFakeAuth(fakeSession()))

    await screen.findByRole('heading', { name: 'Dashboard' })
    expect(screen.getByRole('banner')).toHaveTextContent('user.a@example.com')

    fireEvent.click(screen.getByRole('button', { name: 'Log out' }))

    expect(await screen.findByRole('heading', { name: 'Log in' })).toBeInTheDocument()
    expect(fake.auth.signOut).toHaveBeenCalledTimes(1)
    expect(screen.queryByText('user.a@example.com')).not.toBeInTheDocument()
  })

  it('signs out and explains why when the backend rejects the token', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ detail: 'Authentication required.' }, 401))
    const fake = renderApp('/dashboard', createFakeAuth(fakeSession()))

    expect(await screen.findByText(MESSAGES.sessionEnded)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Log in' })).toBeInTheDocument()
    expect(fake.auth.signOut).toHaveBeenCalled()
    expect(screen.queryByText(/Authentication required/)).not.toBeInTheDocument()
  })

  it('shows a mapped error when the backend fails for another reason', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ detail: 'Authentication service is unavailable.' }, 503))
    renderApp('/dashboard', createFakeAuth(fakeSession()))

    expect(await screen.findByRole('alert')).toHaveTextContent(MESSAGES.unexpected)
  })

  it('redirects to the login page when the session ends elsewhere', async () => {
    const fake = renderApp('/dashboard', createFakeAuth(fakeSession()))
    await screen.findByRole('heading', { name: 'Dashboard' })

    act(() => fake.emit('SIGNED_OUT', null))

    await waitFor(() => expect(screen.getByRole('heading', { name: 'Log in' })).toBeInTheDocument())
  })
})
