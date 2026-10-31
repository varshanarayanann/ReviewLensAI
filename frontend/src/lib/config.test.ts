import { describe, expect, it } from 'vitest'
import { ConfigError, loadConfig } from './config'

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
})
