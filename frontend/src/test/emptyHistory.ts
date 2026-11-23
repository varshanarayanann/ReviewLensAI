import { vi } from 'vitest'

type Fetcher = (url: string, options?: RequestInit) => unknown

// Earlier workspace-story fixtures predate the history GET endpoint. Give that
// new read its own empty response; leave every existing request/failure intact.
// The S3-007 suite supplies real history fixtures without this helper.
export function stubFetchWithEmptyHistory(fetcher: Fetcher) {
  const mock = vi.fn((url: string, options?: RequestInit) => {
    if (typeof url === 'string' && url.includes('/questions?') && options?.method === 'GET') {
      return Promise.resolve(new Response('[]', { status: 200 }))
    }
    return fetcher(url, options)
  })
  vi.stubGlobal('fetch', mock)
  return mock
}
