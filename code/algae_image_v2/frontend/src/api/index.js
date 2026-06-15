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

// ─── Live Stream ──────────────────────────────────────────────

/** Get the N most recent detection results */
export function getLatestResults(n = 10) {
  return api.get('/detect/latest', { params: { n } })
}

/** Get live stream status (fps, frame count, uptime) */
export function getStreamStatus() {
  return api.get('/detect/stream-status')
}

/** Start camera acquisition. exposure_us in microseconds (default 5000=5ms). */
export function startStream(exposure_us = 5000) {
  return api.post('/detect/stream/start', null, { params: { exposure_us } })
}

/** Stop camera acquisition */
export function stopStream() {
  return api.post('/detect/stream/stop')
}

// ─── Video Stream (demo mode) ────────────────────────────────────

/** Start video file as detection source */
export function startVideoStream(videoPath, fps = 10, loop = false) {
  return api.post('/detect/stream/start-video', null, {
    params: { video_path: videoPath, fps, loop },
  })
}

/** Stop video stream */
export function stopVideoStream() {
  return api.post('/detect/stream/stop-video')
}

/** Get video stream status */
export function getVideoStatus() {
  return api.get('/detect/video-status')
}

// ─── Device Management ─────────────────────────────────────────

/** List all devices */
export function getDevices() {
  return api.get('/devices')
}

/** Add a new device */
export function addDevice(name, location, model = 'MV-CA013-20GC') {
  return api.post('/devices', null, { params: { name, location, model } })
}

/** Delete a device */
export function deleteDevice(id) {
  return api.delete(`/devices/${id}`)
}

/** Update device info */
export function updateDevice(id, fields) {
  return api.put(`/devices/${id}`, null, { params: fields })
}

// ─── Review ────────────────────────────────────────────────────

/** List review records */
export function getReviews(status = null) {
  return api.get('/review/list', { params: status ? { status } : {} })
}

/** Submit a review result */
export function submitReview(detectionId, status, correctedClass = null) {
  return api.post('/review/submit', { detection_id: detectionId, status, corrected_class: correctedClass })
}

/** Batch add low-confidence detections to review pool */
export function submitReviewBatch() {
  return api.post('/review/submit-batch')
}

/** Get list of available video files */
export function getVideoList() {
  return api.get('/detect/video-list')
}

export default api
