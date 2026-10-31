import { createContext, useContext } from 'react'
import type { Session, SupabaseClient } from '@supabase/supabase-js'

export type AuthClient = Pick<
  SupabaseClient['auth'],
  'getSession' | 'onAuthStateChange' | 'signInWithPassword' | 'signUp' | 'signOut'
>

export type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated'

export type SignUpResult = 'signed_in' | 'confirmation_required' | 'email_exists'

export interface AuthContextValue {
  status: AuthStatus
  session: Session | null
  signOutReason: string | undefined
  signIn: (email: string, password: string) => Promise<void>
  signUp: (email: string, password: string) => Promise<SignUpResult>
  signOut: () => Promise<void>
  expireSession: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used inside <AuthProvider>')
  return value
}
