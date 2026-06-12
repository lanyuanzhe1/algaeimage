import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getLatestResults, getStreamStatus, startStream, stopStream } from '@/api'

export const useDetectStore = defineStore('detect', () => {
  const currentResult = ref(null)
  const isProcessing = ref(false)
  const error = ref(null)

  // ── Live stream state ──────────────────────────────────────
  const isStreaming = ref(false)
  const liveResults = ref([])
  const streamStatus = ref({ active: false, total_frames: 0, effective_fps: 0, elapsed_seconds: 0 })
  let _pollTimer = null

  function setResult(result) {
    currentResult.value = result
    error.value = null
    liveResults.value.unshift(result)
    if (liveResults.value.length > 50) liveResults.value.length = 50
  }

  function clearResult() {
    currentResult.value = null
    error.value = null
  }

  function setError(msg) {
    error.value = msg
    currentResult.value = null
  }

  // ── Stream control ────────────────────────────────────────

  async function start() {
    const res = await startStream()
    if (res.data.status === 'started') {
      isStreaming.value = true
      startStreamPolling()
    }
    return res.data
  }

  async function stop() {
    stopStreamPolling()
    const res = await stopStream()
    isStreaming.value = false
    liveResults.value = []
    return res.data
  }

  // ── Polling ───────────────────────────────────────────────

  function startStreamPolling() {
    _pollTimer = setInterval(async () => {
      try {
        const [rRes, sRes] = await Promise.all([
          getLatestResults(5),
          getStreamStatus(),
        ])
        liveResults.value = rRes.data.results || []
        streamStatus.value = sRes.data
        if (!sRes.data.active) {
          isStreaming.value = false
        }
      } catch (_e) { /* backend may be starting */ }
    }, 2000)
  }

  function stopStreamPolling() {
    if (_pollTimer) { clearInterval(_pollTimer); _pollTimer = null }
  }

  return {
    currentResult, isProcessing, error, setResult, clearResult, setError,
    isStreaming, liveResults, streamStatus,
    start, stop, startStreamPolling, stopStreamPolling,
  }
})
