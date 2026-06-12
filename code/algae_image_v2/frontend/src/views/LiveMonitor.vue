<template>
  <div class="live-monitor" style="max-width:1200px; margin:0 auto">
    <!-- Control bar -->
    <div class="control-bar">
      <el-button
        type="primary"
        size="large"
        :loading="state === 'starting'"
        :disabled="state === 'running'"
        @click="handleStart"
      >
        <el-icon><VideoPlay /></el-icon>
        开始采集
      </el-button>
      <el-button
        type="danger"
        size="large"
        :loading="state === 'stopping'"
        :disabled="state !== 'running'"
        @click="handleStop"
      >
        <el-icon><VideoPause /></el-icon>
        停止
      </el-button>
      <span class="stream-indicator" :class="state">
        <span class="dot"></span>
        {{ stateText }}
      </span>
      <span v-if="store.streamStatus.total_frames" class="stream-stats">
        {{ store.streamStatus.total_frames }}帧
        {{ store.streamStatus.effective_fps?.toFixed(1) }}fps
      </span>
    </div>

    <!-- Error -->
    <el-alert v-if="errorMsg" :title="errorMsg" type="error" show-icon closable
              style="margin-bottom:16px" @close="errorMsg = null" />

    <!-- Dual panel -->
    <el-row :gutter="16" style="margin-bottom:20px">
      <el-col :xs="24" :md="12">
        <el-card shadow="never" class="image-panel">
          <template #header>
            <span>原始采集图</span>
            <span v-if="rawUrl" style="font-size:12px;color:#999;float:right">
              {{ currentFilename }}
            </span>
          </template>
          <div class="image-wrapper">
            <img v-if="rawUrl" :key="rawUrl" :src="rawUrl" alt="raw" class="live-image" />
            <div v-else class="placeholder">
              <p>{{ placeholderText }}</p>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :md="12">
        <el-card shadow="never" class="image-panel">
          <template #header>
            <span>YOLO 检测结果</span>
            <span v-if="resultUrl" style="font-size:12px;color:#999;float:right">
              {{ detectionSummary }}
            </span>
          </template>
          <div class="image-wrapper">
            <img v-if="resultUrl" :key="resultUrl" :src="resultUrl" alt="result" class="live-image" />
            <div v-else class="placeholder">
              <p>{{ placeholderText }}</p>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Stats + Results -->
    <StatsCards v-if="statsCards.length" :cards="statsCards" style="margin-bottom:16px" />
    <ResultTable
      v-for="(lr, i) in store.liveResults.slice(0, 5)"
      :key="lr.id"
      :detections="lr.detections"
      :style="i === 0 ? '' : 'margin-top:12px;opacity:0.55'"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch, onUnmounted } from 'vue'
import { useDetectStore } from '@/stores/detect'
import StatsCards from '@/components/StatsCards.vue'
import ResultTable from '@/components/ResultTable.vue'

const store = useDetectStore()

// State machine: idle | starting | running | stopping | error
const state = ref('idle')
const errorMsg = ref(null)

// Computed
const stateText = computed(() => ({
  idle: '等待开始',
  starting: '正在启动...',
  running: '采集中',
  stopping: '正在停止...',
  error: '异常',
})[state.value])

const placeholderText = computed(() => {
  if (state.value === 'idle') return '点击「开始采集」启动'
  if (state.value === 'starting') return '正在启动相机...'
  if (state.value === 'error') return errorMsg.value || '采集异常'
  return '等待图像...'
})

const latest = computed(() => store.liveResults[0] || null)
const rawUrl = computed(() => latest.value?.raw_image_url || null)
const resultUrl = computed(() => latest.value?.result_image_url || null)
const currentFilename = computed(() => latest.value?.filename || '')
const detectionSummary = computed(() => {
  if (!latest.value) return ''
  const n = latest.value.detections?.length || 0
  const risk = latest.value.risk_level
  return `${n} 个检出 · ${risk === 'high' ? '高危' : risk === 'medium' ? '中危' : risk === 'low' ? '低危' : '无'}`
})

const statsCards = computed(() => {
  if (!store.liveResults.length) return []
  const lv = latest.value
  const allDets = store.liveResults.flatMap(r => r.detections || [])
  return [
    { label: '检测帧数', value: store.streamStatus.total_frames, sub: '已处理' },
    { label: '最新风险', value: lv?.risk_level || '无', sub: '风险等级',
      color: lv?.risk_level === 'high' ? '#dc2626' : lv?.risk_level === 'medium' ? '#f59e0b' : '#16a34a' },
    { label: '最新 Q 分', value: lv?.q_score?.toFixed(3) || '--', sub: '质量评分' },
    { label: '累计检出', value: allDets.length, sub: '藻类个体' },
    { label: '有效 FPS', value: store.streamStatus.effective_fps?.toFixed(1) || '0.0', sub: '实时帧率' },
  ]
})

// Actions
async function handleStart() {
  state.value = 'starting'
  errorMsg.value = null
  try {
    const res = await store.start()
    if (res.status === 'started') {
      state.value = 'running'
      store.startStreamPolling()
    } else {
      state.value = 'error'
      errorMsg.value = res.detail || '启动失败'
    }
  } catch (e) {
    state.value = 'error'
    errorMsg.value = e.response?.data?.detail || '启动失败，请检查相机连接'
  }
}

async function handleStop() {
  state.value = 'stopping'
  store.stopStreamPolling()
  try {
    await store.stop()
  } catch (e) {
    // ignore stop errors
  }
  state.value = 'idle'
}

// Watch for stream going inactive externally (e.g. camera disconnected)
watch(() => store.streamStatus.active, (active) => {
  if (!active && state.value === 'running') {
    state.value = 'idle'
    store.stopStreamPolling()
    errorMsg.value = '采集已中断，请检查相机连接'
  }
})

onUnmounted(() => {
  store.stopStreamPolling()
})
</script>

<style scoped>
.control-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding: 12px 16px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.stream-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
}
.stream-indicator .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ccc;
}
.stream-indicator.running .dot {
  background: #67c23a;
  animation: pulse 1.5s infinite;
}
.stream-indicator.error .dot {
  background: #dc2626;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}
.stream-stats {
  font-size: 12px;
  color: #67c23a;
  margin-left: auto;
}
.image-panel {
  height: 100%;
}
.image-panel :deep(.el-card__body) {
  padding: 0;
}
.image-wrapper {
  width: 100%;
  aspect-ratio: 4/3;
  background: #1a1a2e;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.live-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.placeholder {
  text-align: center;
  color: #666;
}
.placeholder p {
  margin-top: 8px;
  font-size: 13px;
}
</style>
