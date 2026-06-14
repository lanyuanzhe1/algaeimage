import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

// Minimal test — verify test infrastructure works
describe('detect store — basic', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('Pinia works', () => {
    const pinia = createPinia()
    expect(pinia).toBeDefined()
  })

  it('store can be imported without error', async () => {
    const { useDetectStore } = await import('@/stores/detect')
    const store = useDetectStore()
    expect(store).toBeDefined()
    expect(store.isStreaming).toBe(false)
    expect(store.streamMode).toBeNull()
  })
})
