import { useState } from 'react'
import { useNavigate } from 'react-router'
import { useAuth } from '../../lib/auth/AuthContext'

export function AccountMenu() {
  const { session, signOut } = useAuth()
  const navigate = useNavigate()
  const [loggingOut, setLoggingOut] = useState(false)

  async function handleLogOut() {
    setLoggingOut(true)
    try {
      await signOut()
    } finally {
      navigate('/login', { replace: true })
    }
  }

  return (
    <div className="account-menu">
      <span className="account-menu__email">{session?.user.email}</span>
      <button type="button" className="button button--secondary" onClick={handleLogOut} disabled={loggingOut}>
        {loggingOut ? 'Logging out...' : 'Log out'}
      </button>
    </div>
  )
}
