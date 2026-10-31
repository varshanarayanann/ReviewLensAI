export interface HealthResponse {
  status: string
}

export interface CurrentUserResponse {
  id: string
  email: string | null
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
