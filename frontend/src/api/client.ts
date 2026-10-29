import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || ''

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
})

// Structured error handling — never silently swallow DB errors
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const status = err.response?.status
    const detail = err.response?.data?.detail ?? err.message
    if (status === 503) {
      console.error('[SupplyLens] Database unavailable:', detail)
    }
    return Promise.reject(err)
  },
)
