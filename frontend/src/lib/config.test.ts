import { describe, expect, it } from 'vitest'
import { ConfigError, isSupabaseSecretKey, loadConfig } from './config'

function fakeJwt(payload: Record<string, unknown>): string {
  const encode = (value: Record<string, unknown>) =>
    btoa(JSON.stringify(value)).replace(/=+$/, '').replace(/\+/g, '-').replace(/\//g, '_')
  return `${encode({ alg: 'HS256', typ: 'JWT' })}.${encode(payload)}.test-signature`
}

const base = { VITE_API_BASE_URL: 'http://localhost:8000' }

describe('loadConfig', () => {
  it('reads the API base URL and strips trailing slashes', () => {
    expect(loadConfig({ VITE_API_BASE_URL: 'http://localhost:8000/' })).toEqual({
      apiBaseUrl: 'http://localhost:8000',
    })
  })

  it('fails with a clear message when the API base URL is missing', () => {
    expect(() => loadConfig({})).toThrow(ConfigError)
    expect(() => loadConfig({ VITE_API_BASE_URL: '  ' })).toThrow(/VITE_API_BASE_URL is not set/)
  })

  it('accepts a Supabase anon key', () => {
    const env = { ...base, VITE_SUPABASE_ANON_KEY: fakeJwt({ role: 'anon' }) }

    expect(loadConfig(env).apiBaseUrl).toBe('http://localhost:8000')
  })

  it('accepts a Supabase publishable key', () => {
    const env = { ...base, VITE_SUPABASE_ANON_KEY: 'sb_publishable_test_key' }

    expect(loadConfig(env).apiBaseUrl).toBe('http://localhost:8000')
  })

  it('refuses to start with a service-role key in a VITE_ variable', () => {
    const env = { ...base, VITE_SUPABASE_ANON_KEY: fakeJwt({ role: 'service_role' }) }

    expect(() => loadConfig(env)).toThrow(ConfigError)
    expect(() => loadConfig(env)).toThrow(/VITE_SUPABASE_ANON_KEY contains a Supabase secret/)
  })

  it('refuses to start with a Supabase secret key in any VITE_ variable', () => {
    const env = { ...base, VITE_SOMETHING_ELSE: 'sb_secret_test_key' }

    expect(() => loadConfig(env)).toThrow(/VITE_SOMETHING_ELSE contains a Supabase secret/)
  })

  it('does not echo the secret key value in the error message', () => {
    const secret = fakeJwt({ role: 'service_role' })

    expect(() => loadConfig({ ...base, VITE_SUPABASE_ANON_KEY: secret })).toThrow(
      expect.objectContaining({ message: expect.not.stringContaining(secret) }),
    )
  })
})

describe('isSupabaseSecretKey', () => {
  it.each([
    ['not-a-jwt', false],
    ['a.b.c', false],
    ['', false],
  ])('treats %j as not a secret key', (value, expected) => {
    expect(isSupabaseSecretKey(value)).toBe(expected)
  })
})
