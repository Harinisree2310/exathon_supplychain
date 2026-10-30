import axios from 'axios'

interface ApiErrorResponse {
  detail?: unknown
}

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError<ApiErrorResponse>(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return detail
    return error.message
  }

  return error instanceof Error ? error.message : 'An unexpected error occurred'
}
