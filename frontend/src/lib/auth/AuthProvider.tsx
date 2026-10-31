import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import type { Session } from '@supabase/supabase-js'
import { MESSAGES } from '../messages'
import { AuthContext, type AuthClient, type AuthContextValue, type SignUpResult } from './AuthContext'

interface AuthProviderProps {
  client: AuthClient
  children: ReactNode
}

export function AuthProvider({ client, children }: AuthProviderProps) {
  const [session, setSession] = useState<Session | null>(null)
  const [restored, setRestored] = useState(false)
  const [signOutReason, setSignOutReason] = useState<string>()

  useEffect(() => {
    let active = true
    client
      .getSession()
      .then(({ data }) => active && setSession(data.session))
      .catch(() => active && setSession(null))
      .finally(() => active && setRestored(true))

    const { data } = client.onAuthStateChange((_event, nextSession) => {
      if (!active) return
      setSession(nextSession)
      setRestored(true)
    })
    return () => {
      active = false
      data.subscription.unsubscribe()
    }
  }, [client])

  const signIn = useCallback(
    async (email: string, password: string) => {
      const { data, error } = await client.signInWithPassword({ email, password })
      if (error) throw error
      setSignOutReason(undefined)
      setSession(data.session)
    },
    [client],
  )

  const signUp = useCallback(
    async (email: string, password: string): Promise<SignUpResult> => {
      const { data, error } = await client.signUp({
        email,
        password,
        options: { emailRedirectTo: `${window.location.origin}/login` },
      })
      if (error) throw error
      if (data.session) {
        setSignOutReason(undefined)
        setSession(data.session)
        return 'signed_in'
      }
      // With email confirmation on, Supabase hides existing accounts by returning a user with no identities.
      if (data.user && data.user.identities?.length === 0) return 'email_exists'
      return 'confirmation_required'
    },
    [client],
  )

  const signOut = useCallback(async () => {
    try {
      await client.signOut()
    } finally {
      setSession(null)
    }
  }, [client])

  const expireSession = useCallback(async () => {
    setSignOutReason(MESSAGES.sessionEnded)
    await signOut()
  }, [signOut])

  const value = useMemo<AuthContextValue>(
    () => ({
      status: !restored ? 'loading' : session ? 'authenticated' : 'unauthenticated',
      session,
      signOutReason,
      signIn,
      signUp,
      signOut,
      expireSession,
    }),
    [restored, session, signOutReason, signIn, signUp, signOut, expireSession],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
