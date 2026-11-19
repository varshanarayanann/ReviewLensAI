export interface HealthResponse {
  status: string
}

export interface CurrentUserResponse {
  id: string
  email: string | null
}

export interface WorkspaceTargetResponse {
  id: string
  name: string
  platform: 'google_maps'
  source_url: string
}

export interface AnalysisTargetResponse extends WorkspaceTargetResponse {
  created_at: string
}

export interface IngestionResultResponse {
  run_id: string
  target_id: string
  state: 'processing' | 'succeeded' | 'partial' | 'failed'
  persisted_count: number
  rejected_count: number
  message: string
}

export interface ReviewSummaryResponse {
  target_id: string
  review_count: number
  average_rating: number | null
}

export interface PersistedReviewResponse {
  id: string
  target_id: string
  run_id: string
  review_text: string
  rating: number
}

export function getSavedReviews(base: string, targetId: string, token: string, offset: number, signal: AbortSignal) {
  return targetRequest<PersistedReviewResponse[]>(
    base, `/${encodeURIComponent(targetId)}/reviews?limit=20&offset=${offset}`, token, undefined, signal,
  )
}

export interface ReviewAnswerResponse {
  target_id: string
  status: 'answered' | 'insufficient_evidence' | 'out_of_scope' | 'no_reviews'
  answer: string | null
  review_count: number
}

export interface QuestionExchangeResponse extends ReviewAnswerResponse {
  id: string
  question: string
  created_at: string
}

export function getQuestionHistory(base: string, targetId: string, token: string, offset: number, signal: AbortSignal) {
  return targetRequest<QuestionExchangeResponse[]>(
    base, `/${encodeURIComponent(targetId)}/questions?limit=50&offset=${offset}`, token, undefined, signal,
  )
}

export function askReviewQuestion(base: string, targetId: string, token: string, question: string, signal: AbortSignal) {
  return targetRequest<ReviewAnswerResponse>(
    base, `/${encodeURIComponent(targetId)}/questions`, token, { question }, signal,
  )
}

export async function getWorkspace(base: string, targetId: string, token: string) {
  const path = `/${encodeURIComponent(targetId)}`
  const target = await targetRequest<WorkspaceTargetResponse>(base, path, token)
  const result = await targetRequest<IngestionResultResponse | null>(base, `${path}/ingestions/latest`, token)
  return { target, result }
}

export function getReviewSummary(base: string, targetId: string, token: string) {
  return targetRequest<ReviewSummaryResponse>(
    base, `/${encodeURIComponent(targetId)}/reviews/summary`, token,
  )
}

export function collectGoogleMapsReviews(base: string, targetId: string, token: string) {
  return targetRequest<IngestionResultResponse>(
    base, `/${encodeURIComponent(targetId)}/ingestions/google-maps`, token, {},
  )
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

export async function deleteTarget(base: string, targetId: string, token: string, signal: AbortSignal): Promise<void> {
  const response = await fetch(`${base}/api/targets/${encodeURIComponent(targetId)}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
    signal,
  })
  if (!response.ok) throw new ApiError(response.status)
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

export async function targetRequest<T>(base: string, path: string, token: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${base}/api/targets${path}`, {
    method: body === undefined ? 'GET' : 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    ...(signal ? { signal } : {}),
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  })
  if (!response.ok) throw new ApiError(response.status)
  return response.json() as Promise<T>
}
