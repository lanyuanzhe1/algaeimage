import { vi } from 'vitest'

// Mock the API module — prevents axios from loading in jsdom
vi.mock('@/api', () => ({
  getLatestResults: vi.fn(() => Promise.resolve({ data: { results: [{ id: 1, filename: 'fake.jpg' }] } })),
  getStreamStatus: vi.fn(() => Promise.resolve({ data: { active: false, total_frames: 0, effective_fps: 0, elapsed_seconds: 0 } })),
  startStream: vi.fn(() => Promise.resolve({ data: { status: 'started' } })),
  stopStream: vi.fn(() => Promise.resolve({ data: { status: 'stopped' } })),
  startVideoStream: vi.fn(() => Promise.resolve({ data: { status: 'started' } })),
  stopVideoStream: vi.fn(() => Promise.resolve({ data: { status: 'stopped' } })),
  getVideoList: vi.fn(() => Promise.resolve({ data: { videos: [] } })),
}))
