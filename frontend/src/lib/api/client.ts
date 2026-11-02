export interface HealthResponse {
  status: string
}

export interface CurrentUserResponse {
  id: string
  email: string | null
}

export interface AnalysisTargetResponse {
  id: string
  name: string
  platform: 'google_maps'
  source_url: string
  created_at: string
}

export async function getTargets(
  apiBaseUrl: string,
  accessToken: string,
): Promise<AnalysisTargetResponse[]> {
  const response = await fetch(`${apiBaseUrl}/api/targets`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  if (!response.ok) throw new ApiError(response.status)
  return (await response.json()) as AnalysisTargetResponse[]
}

export class ApiError extends Error {
  readonly status: number

  constructor(status: number) {
    super(`API request failed with status ${status}`)
    this.status = status
  }
}

export async function getHealth(apiBaseUrl: string): Promise<HealthResponse> {
  const response = await fetch(`${apiBaseUrl}/api/health`)
  if (!response.ok) {
    throw new ApiError(response.status)
  }
  return (await response.json()) as HealthResponse
}

export async function getCurrentUser(
  apiBaseUrl: string,
  accessToken: string,
): Promise<CurrentUserResponse> {
  const response = await fetch(`${apiBaseUrl}/api/me`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  if (!response.ok) {
    throw new ApiError(response.status)
  }
  return (await response.json()) as CurrentUserResponse
}

export async function targetRequest<T>(base: string, path: string, token: string, body?: unknown): Promise<T> {
  const response = await fetch(`${base}/api/targets${path}`, {
    method: body === undefined ? 'GET' : 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  })
  if (!response.ok) throw new ApiError(response.status)
  return response.json() as Promise<T>
}
