import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  getLatestResults, getStreamStatus,
  startStream, stopStream,
  startVideoStream, stopVideoStream,
  getVideoList,
} from '@/api'

export const useDetectStore = defineStore('detect', () => {
  const currentResult = ref(null)
  const isProcessing = ref(false)
  const error = ref(null)

  // ── Live stream state ──────────────────────────────────────
  const isStreaming = ref(false)
  const streamMode = ref(null)  // 'camera' | 'video' | null
  const liveResults = ref([])
  const streamStatus = ref({ active: false, total_frames: 0, effective_fps: 0, elapsed_seconds: 0 })
  const exposureUs = ref(5000)  // microseconds
  const videoPath = ref('')
  const videoFps = ref(10)
  const videoLoop = ref(true)
  const videoOptions = ref([])  // dynamic: fetched from backend
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

  // ── Camera stream ─────────────────────────────────────────

  async function start() {
    const res = await startStream(exposureUs.value)
    if (res.data.status === 'started') {
      streamMode.value = 'camera'
      isStreaming.value = true
      startStreamPolling()
    }
    return res.data
  }

  // ── Video stream ──────────────────────────────────────────

  async function fetchVideoList() {
    try {
      const res = await getVideoList()
      const list = res.data.videos || []
      videoOptions.value = list.map(v => ({
        label: `${v.name} (${v.size_mb}MB)`,
        path: v.path,
      }))
      // Auto-select first if none chosen
      if (!videoPath.value && list.length) {
        videoPath.value = list[0].path
      }
    } catch (_e) { /* backend may not be ready */ }
  }

  async function startVideo() {
    const res = await startVideoStream(videoPath.value, videoFps.value, videoLoop.value)
    if (res.data.status === 'started') {
      streamMode.value = 'video'
      isStreaming.value = true
      startStreamPolling()
    }
    return res.data
  }

  // ── Stop (camera or video) ────────────────────────────────

  async function stop() {
    stopStreamPolling()
    try {
      if (streamMode.value === 'video') {
        await stopVideoStream()
      } else {
        await stopStream()
      }
    } catch (_e) { /* API may already be down */ }
    isStreaming.value = false
    streamMode.value = null
    liveResults.value = []
  }

  // ── Survive component remount ──────────────────────────────

  async function checkLiveStatus() {
    try {
      const res = await getStreamStatus()
      if (res.data && res.data.active) {
        isStreaming.value = true
        if (!streamMode.value) streamMode.value = 'camera'
        startStreamPolling()
      }
    } catch (_e) { /* not streaming */ }
  }

  // ── Polling ───────────────────────────────────────────────

  function startStreamPolling() {
    if (_pollTimer) return  // already polling
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
    isStreaming, streamMode, liveResults, streamStatus,
    exposureUs, videoPath, videoFps, videoLoop, videoOptions,
    start, startVideo, fetchVideoList, stop, checkLiveStatus, startStreamPolling, stopStreamPolling,
  }
})
