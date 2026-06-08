import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 120000,
})

// ─── Detection ──────────────────────────────────────────────

/** Upload single image with pipeline visualization */
export function detectVisualize(file) {
  const form = new FormData()
  form.append('file', file)
  return api.post('/detect/visualize', form)
}

/** Upload single image (simple detection, no viz) */
export function detectSingle(file) {
  const form = new FormData()
  form.append('file', file)
  return api.post('/detect', form)
}

// ─── Dashboard ──────────────────────────────────────────────

export function getStats() {
  return api.get('/dashboard/stats')
}

// ─── History ────────────────────────────────────────────────

export function getHistory(page = 1, limit = 20) {
  return api.get('/history', { params: { page, limit } })
}

export function getHistoryDetail(id) {
  return api.get(`/history/${id}`)
}

export function deleteHistory(id) {
  return api.delete(`/history/${id}`)
}

export default api
