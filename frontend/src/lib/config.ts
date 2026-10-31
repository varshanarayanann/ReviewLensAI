export interface AppConfig {
  apiBaseUrl: string
  supabaseUrl: string
  supabaseAnonKey: string
}

export class ConfigError extends Error {}

type Env = Record<string, string | undefined>

const SUPABASE_SECRET_KEY_PREFIX = 'sb_secret_'

function jwtRole(token: string): unknown {
  const parts = token.split('.')
  if (parts.length !== 3) return undefined
  try {
    const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/')
    const padded = base64.padEnd(Math.ceil(base64.length / 4) * 4, '=')
    return (JSON.parse(atob(padded)) as { role?: unknown }).role
  } catch {
    return undefined
  }
}

export function isSupabaseSecretKey(value: string): boolean {
  const trimmed = value.trim()
  return trimmed.startsWith(SUPABASE_SECRET_KEY_PREFIX) || jwtRole(trimmed) === 'service_role'
}

function assertNoSecretKeys(env: Env): void {
  const exposed = Object.entries(env)
    .filter(([name, value]) => name.startsWith('VITE_') && typeof value === 'string')
    .filter(([, value]) => isSupabaseSecretKey(value as string))
    .map(([name]) => name)
  if (exposed.length > 0) {
    throw new ConfigError(
      `${exposed.join(', ')} contains a Supabase secret (service-role) key. ` +
        'Secret keys must never be used in the frontend: use the anon/publishable key instead, ' +
        'and rotate the exposed key in the Supabase dashboard.',
    )
  }
}

function required(env: Env, name: string): string {
  const value = env[name]?.trim()
  if (!value) {
    throw new ConfigError(
      `${name} is not set. Copy frontend/.env.example to frontend/.env and fill in the values.`,
    )
  }
  return value
}

export function loadConfig(env: Env = import.meta.env): AppConfig {
  assertNoSecretKeys(env)

  return {
    apiBaseUrl: required(env, 'VITE_API_BASE_URL').replace(/\/+$/, ''),
    supabaseUrl: required(env, 'VITE_SUPABASE_URL').replace(/\/+$/, ''),
    supabaseAnonKey: required(env, 'VITE_SUPABASE_ANON_KEY'),
  }
}
