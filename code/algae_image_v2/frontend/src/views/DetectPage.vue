<template>
  <div class="detect-page" style="max-width:1200px; margin:0 auto">
    <!-- Live mode toggle -->
    <el-card shadow="never" style="margin-bottom:20px">
      <div style="display:flex;align-items:center;gap:16px">
        <el-switch
          v-model="liveMode"
          @change="toggleLiveMode"
          active-text="实时监测"
          inactive-text="手动检测"
        />
        <span v-if="liveMode" style="font-size:13px;color:#67c23a">
          运行中 | 已处理 {{ streamStatus.total_frames }} 帧 |
          有效 {{ streamStatus.effective_fps }} fps |
          运行 {{ streamStatus.elapsed_seconds }}s
        </span>
        <span v-else style="font-size:13px;color:#999">
          选择图片文件手动检测
        </span>
      </div>
    </el-card>

    <!-- Upload area -->
    <el-card v-if="!liveMode" shadow="never" style="margin-bottom:20px">
      <el-upload
        ref="uploadRef"
        drag
        :auto-upload="false"
        :limit="1"
        accept="image/*"
        :on-change="handleFileChange"
        :on-remove="handleRemove"
        :file-list="fileList"
      >
        <el-icon :size="48"><UploadFilled /></el-icon>
        <div style="margin-top:12px; font-size:15px">
          拖拽或<em>点击上传</em>藻类显微图像
        </div>
        <template #tip>
          <div style="margin-top:8px; font-size:12px; color:#999">
            支持 PNG / JPG / TIF / BMP 格式
          </div>
        </template>
      </el-upload>

      <div style="text-align:center; margin-top:16px">
        <el-button
          type="primary"
          size="large"
          :loading="isProcessing"
          :disabled="!selectedFile"
          @click="runDetection"
        >
          {{ isProcessing ? '检测中...' : '开始检测' }}
        </el-button>
      </div>
    </el-card>

    <!-- Error -->
    <el-alert v-if="error" :title="error" type="error" show-icon closable
              style="margin-bottom:20px" @close="error = null" />

    <!-- Live results (streaming mode) -->
    <template v-if="liveMode && liveResults.length">
      <PipelineViz
        v-if="liveResults[0].steps"
        :steps="liveResults[0].steps"
      />
      <StatsCards
        v-if="liveStatsCards.length"
        :cards="liveStatsCards"
        style="margin-top:20px"
      />
      <ResultTable
        v-for="(lr, i) in liveResults.slice(0, 5)"
        :key="lr.id"
        :detections="lr.detections"
        :style="i === 0 ? 'margin-top:12px' : 'margin-top:12px;opacity:0.55'"
      />
      <div v-if="liveResults.length > 5" style="text-align:center;margin-top:8px;font-size:12px;color:#888">
        ... 还有 {{ liveResults.length - 5 }} 条历史结果
      </div>
    </template>

    <!-- Pipeline visualization -->
    <PipelineViz v-if="result && result.steps" :steps="result.steps" />

    <!-- Stats cards -->
    <StatsCards
      v-if="result"
      :cards="statsCards"
      style="margin-top:20px"
    />

    <!-- Detection table -->
    <ResultTable v-if="result && result.detections.length" :detections="result.detections" />

    <!-- Charts row -->
    <el-row v-if="result && result.detections.length" :gutter="16" style="margin-top:20px">
      <el-col :xs="24" :md="12">
        <el-card shadow="never">
          <template #header>风险分布</template>
          <v-chart :option="riskPieOption" style="height:280px" autoresize />
        </el-card>
      </el-col>
      <el-col :xs="24" :md="12">
        <el-card shadow="never">
          <template #header>置信度分布</template>
          <v-chart :option="confBarOption" style="height:280px" autoresize />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onBeforeUnmount } from 'vue'
import VChart from 'vue-echarts'
import { detectVisualize, getLatestResults, getStreamStatus } from '@/api'
import PipelineViz from '@/components/PipelineViz.vue'
import StatsCards from '@/components/StatsCards.vue'
import ResultTable from '@/components/ResultTable.vue'

const selectedFile = ref(null)
const fileList = ref([])
const isProcessing = ref(false)
const result = ref(null)
const error = ref(null)

// ── Live stream mode ──────────────────────────────────────────
const liveMode = ref(false)
const liveResults = ref([])
const streamStatus = ref({ active: false, total_frames: 0, effective_fps: 0, elapsed_seconds: 0 })
let _pollTimer = null

function toggleLiveMode() {
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
        getLatestResults(10),
        getStreamStatus(),
      ])
      liveResults.value = rRes.data.results || []
      streamStatus.value = sRes.data
    } catch (_e) {
      // Silently skip — backend may be starting up
    }
  }, 2000)
}

function stopPolling() {
  if (_pollTimer) {
    clearInterval(_pollTimer)
    _pollTimer = null
  }
}

onBeforeUnmount(() => stopPolling())

function handleFileChange(file) {
  selectedFile.value = file.raw
}

function handleRemove() {
  selectedFile.value = null
  result.value = null
  error.value = null
}

async function runDetection() {
  if (!selectedFile.value) return
  isProcessing.value = true
  error.value = null
  result.value = null

  try {
    const res = await detectVisualize(selectedFile.value)
    result.value = res.data
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || '检测失败，请重试'
  } finally {
    isProcessing.value = false
  }
}

const liveStatsCards = computed(() => {
  if (!liveResults.value.length) return []
  const latest = liveResults.value[0]
  const allDets = liveResults.value.flatMap(r => r.detections || [])
  return [
    { label: '检测帧数', value: streamStatus.value.total_frames, sub: '已处理' },
    { label: '最新风险', value: latest.risk_level || '无', sub: '风险等级', color: latest.risk_level === 'high' ? '#dc2626' : latest.risk_level === 'medium' ? '#f59e0b' : '#16a34a' },
    { label: '最新 Q 分', value: latest.q_score?.toFixed(3) || '--', sub: '质量评分' },
    { label: '累计检出', value: allDets.length, sub: '藻类个体' },
    { label: '有效 FPS', value: streamStatus.value.effective_fps?.toFixed(1) || '0.0', sub: '实时帧率' },
  ]
})

const statsCards = computed(() => {
  if (!result.value) return []
  const r = result.value
  const highCount = r.detections.filter(d => d.risk_level === 'high').length
  return [
    { label: '检测总数', value: r.detections.length, sub: '检出藻类个体' },
    { label: '高危预警', value: highCount, sub: '需立即关注', color: highCount ? '#dc2626' : '#16a34a' },
    { label: '质量评分', value: r.q_score.toFixed(2), sub: 'Q Score', color: r.q_score > 0.7 ? '#16a34a' : '#f59e0b' },
    { label: '处理耗时', value: (r.processing_time_ms / 1000).toFixed(1) + 's', sub: '端到端时间' },
    { label: '使用模型', value: 'YOLOv8l', sub: 'FMPD 5类' },
  ]
})

const riskPieOption = computed(() => {
  const dist = { high: 0, medium: 0, low: 0 }
  result.value?.detections.forEach(d => { dist[d.risk_level]++ })
  return {
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      label: { show: true, formatter: '{b}: {c}' },
      data: [
        { value: dist.high, name: '高危', itemStyle: { color: '#dc2626' } },
        { value: dist.medium, name: '中危', itemStyle: { color: '#f59e0b' } },
        { value: dist.low, name: '低危', itemStyle: { color: '#16a34a' } },
      ],
    }],
  }
})

const confBarOption = computed(() => {
  const names = result.value?.detections.map(d => d.class_name_zh) || []
  const confs = result.value?.detections.map(d => +(d.confidence * 100).toFixed(1)) || []
  return {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: names, axisLabel: { rotate: 30 } },
    yAxis: { type: 'value', name: '置信度 (%)', max: 100 },
    series: [{
      type: 'bar',
      data: confs,
      itemStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [{ offset: 0, color: '#2d6a9f' }, { offset: 1, color: '#1a3a5c' }],
        },
      },
    }],
    grid: { left: 50, right: 20, top: 20, bottom: 60 },
  }
})
</script>
