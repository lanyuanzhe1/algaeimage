import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getLatestResults, getStreamStatus } from '@/api'

export const useDetectStore = defineStore('detect', () => {
  const currentResult = ref(null)
  const isProcessing = ref(false)
  const error = ref(null)

  // ── Live stream state ──────────────────────────────────────
  const liveMode = ref(false)
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

  // ── Live mode ──────────────────────────────────────────────
  function toggleLiveMode() {
    liveMode.value = !liveMode.value
    if (liveMode.value) {
      startPolling()
    } else {
      stopPolling()
    }
  }

  function startPolling() {
    _pollTimer = setInterval(async () => {
      try {
        const [rRes, sRes] = await Promise.all([
          getLatestResults(5),
          getStreamStatus(),
        ])
        liveResults.value = rRes.data.results || []
        streamStatus.value = sRes.data
      } catch (_e) { /* backend may be starting */ }
    }, 2000)
  }

  function stopPolling() {
    if (_pollTimer) { clearInterval(_pollTimer); _pollTimer = null }
  }

  return {
    currentResult, isProcessing, error, setResult, clearResult, setError,
    liveMode, liveResults, streamStatus, toggleLiveMode, startPolling, stopPolling
  }
})
