export interface AppConfig {
  apiBaseUrl: string
}

export class ConfigError extends Error {}

export function loadConfig(env: Record<string, string | undefined> = import.meta.env): AppConfig {
  const apiBaseUrl = env.VITE_API_BASE_URL?.trim()
  if (!apiBaseUrl) {
    throw new ConfigError(
      'VITE_API_BASE_URL is not set. Copy frontend/.env.example to frontend/.env and fill in the values.',
    )
  }
  return { apiBaseUrl: apiBaseUrl.replace(/\/+$/, '') }
}
