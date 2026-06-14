import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

// Use vi.hoisted to ensure mock runs before ANY imports
const { mockAxios } = vi.hoisted(() => {
  const mockAxios = {
    get: vi.fn(() => Promise.resolve({ data: {} })),
    post: vi.fn(() => Promise.resolve({ data: {} })),
    delete: vi.fn(() => Promise.resolve({ data: {} })),
  }
  return { mockAxios }
})

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => mockAxios),
  },
}))

// Now safe to import — axios is mocked
import { useDetectStore } from '@/stores/detect'

describe('useDetectStore — stream lifecycle', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  // ── Bug 1 core: stop() must actually stop ────────────────────
  it('stop() sets isStreaming=false and streamMode=null', async () => {
    const store = useDetectStore()

    await store.start()
    expect(store.isStreaming).toBe(true)
    expect(store.streamMode).toBe('camera')

    await store.stop()
    expect(store.isStreaming).toBe(false)
    expect(store.streamMode).toBeNull()
  })

  // ── Bug 1: stop must clear the polling timer ─────────────────
  it('stop() clears the polling interval', async () => {
    const store = useDetectStore()

    await store.start()
    await vi.advanceTimersByTimeAsync(2500)
    expect(store.liveResults.length).toBeGreaterThan(0)

    await store.stop()
    const countAfterStop = store.liveResults.length
    await vi.advanceTimersByTimeAsync(10000)
    expect(store.liveResults.length).toBe(countAfterStop)
  })

  // ── Bug 2 root: state must survive component remount ─────────
  it('isStreaming and streamMode persist across remount', () => {
    const store = useDetectStore()
    store.isStreaming = true
    store.streamMode = 'video'

    const store2 = useDetectStore() // simulates component remount
    expect(store2.isStreaming).toBe(true)
    expect(store2.streamMode).toBe('video')
  })
})
