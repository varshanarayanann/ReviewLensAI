import { vi } from 'vitest'

// Earlier workspace-story fixtures predate the history GET endpoint. Give that
// new read its own empty response; leave every existing request/failure intact.
// The S3-007 suite supplies real history fixtures without this helper.
export function stubFetchWithEmptyHistory(fetcher: (url: string, options?: RequestInit) => unknown) {
  vi.stubGlobal('fetch', (url: string, options?: RequestInit) => {
    if (url.includes('/questions?') && options?.method === 'GET') {
      return Promise.resolve(new Response('[]', { status: 200 }))
    }
    return fetcher(url, options)
  })
}
