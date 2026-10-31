import { vi } from 'vitest'
import type { AuthChangeEvent, Session } from '@supabase/supabase-js'
import type { AuthClient } from '../lib/auth/AuthContext'

type Listener = (event: AuthChangeEvent, session: Session | null) => void

export function fakeSession(email = 'user.a@example.com'): Session {
  return {
    access_token: 'test-access-token',
    refresh_token: 'test-refresh-token',
    token_type: 'bearer',
    expires_in: 3600,
    user: { id: 'user-a-id', email, aud: 'authenticated', app_metadata: {}, user_metadata: {}, created_at: '' },
  } as Session
}

export function createFakeAuth(initialSession: Session | null = null) {
  const listeners = new Set<Listener>()
  const auth = {
    getSession: vi.fn(async () => ({ data: { session: initialSession }, error: null })),
    onAuthStateChange: vi.fn((listener: Listener) => {
      listeners.add(listener)
      return { data: { subscription: { unsubscribe: () => listeners.delete(listener) } } }
    }),
    signInWithPassword: vi.fn(),
    signUp: vi.fn(),
    signOut: vi.fn(async () => ({ error: null })),
  }

  return {
    auth,
    client: auth as unknown as AuthClient,
    emit(event: AuthChangeEvent, session: Session | null) {
      listeners.forEach((listener) => listener(event, session))
    },
  }
}
