<template>
  <div class="home-page">
    <!-- ═══ Metrics Bar ═══ -->
    <MetricsBar />

    <!-- ═══ 3-Column Layout ═══ -->
    <el-row :gutter="20">
      <!-- Left Panel: Stats + Quick Actions -->
      <el-col :xs="24" :md="6">
        <el-card shadow="never" style="margin-bottom:16px">
          <template #header>
            <span style="font-weight:600; font-size:15px">数据概览</span>
            <p style="font-size:12px; color:#999; margin-top:2px">实时统计 · 快速操作</p>
          </template>

          <div class="stat-list">
            <div class="stat-item">
              <div class="stat-num">{{ statsData.total_detections ?? '--' }}</div>
              <div class="stat-text">总检测次数</div>
            </div>
            <div class="stat-item">
              <div class="stat-num">{{ statsData.today_count ?? '--' }}</div>
              <div class="stat-text">今日检测</div>
            </div>
            <div class="stat-item">
              <div class="stat-num" :style="{ color: (statsData.risk_distribution?.high || 0) > 0 ? '#dc2626' : '#16a34a' }">
                {{ statsData.risk_distribution?.high ?? '--' }}
              </div>
              <div class="stat-text">高危预警</div>
            </div>
          </div>

          <div class="quick-actions">
            <el-button type="primary" size="large" style="width:100%" @click="scrollToDetect">
              开始新检测
            </el-button>
            <el-button size="large" style="width:100%; margin-top:8px" @click="$router.push('/history')">
              查看历史记录
            </el-button>
          </div>
        </el-card>

        <!-- Pipeline overview -->
        <el-card shadow="never">
          <template #header>
            <span style="font-weight:600; font-size:15px">检测管线</span>
            <p style="font-size:12px; color:#999; margin-top:2px">五步处理流程</p>
          </template>
          <div class="pipeline-mini">
            <div class="pipe-item"><span class="pipe-num">1</span><span>偏振采集</span></div>
            <div class="pipe-arrow">→</div>
            <div class="pipe-item"><span class="pipe-num">2</span><span>偏振模拟</span></div>
            <div class="pipe-arrow">→</div>
            <div class="pipe-item"><span class="pipe-num">3</span><span>图像增强</span></div>
            <div class="pipe-arrow">→</div>
            <div class="pipe-item"><span class="pipe-num">4</span><span>YOLO识别</span></div>
            <div class="pipe-arrow">→</div>
            <div class="pipe-item"><span class="pipe-num">5</span><span>融合预警</span></div>
          </div>
        </el-card>
      </el-col>

      <!-- Center Panel: Upload + Detection -->
      <el-col :xs="24" :md="12" id="detectZone">
        <el-card shadow="never" style="margin-bottom:16px">
          <template #header>
            <span style="font-weight:600; font-size:15px">快速检测</span>
            <p style="font-size:12px; color:#999; margin-top:2px">上传藻类显微图像 · 偏振分析 · YOLO识别</p>
          </template>

          <!-- Upload Zone -->
          <el-upload
            ref="uploadRef"
            drag
            :auto-upload="false"
            :limit="50"
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
                支持 PNG / JPG / TIF / BMP 格式，最多 50 张
              </div>
            </template>
          </el-upload>

          <div style="text-align:center; margin-top:16px; display:flex; gap:12px; justify-content:center; flex-wrap:wrap">
            <el-button
              type="primary"
              size="large"
              :loading="isProcessing"
              :disabled="!selectedFile"
              @click="runDetection"
            >
              {{ isProcessing ? '检测中...' : '单图检测' }}
            </el-button>
            <el-button
              size="large"
              :disabled="fileList.length < 2 || isProcessing"
              @click="runBatchDetection"
            >
              批量处理
            </el-button>
          </div>

          <p v-if="fileList.length" style="text-align:center; font-size:12px; color:#999; margin-top:8px">
            已选择 {{ fileList.length }} 个文件
          </p>

          <!-- Progress -->
          <div v-if="isProcessing" style="margin-top:16px">
            <el-progress :percentage="progressPct" :stroke-width="8" />
            <p style="text-align:center; font-size:12px; color:#999; margin-top:4px">{{ progressText }}</p>
          </div>

          <!-- Error -->
          <el-alert
            v-if="error"
            :title="error"
            type="error"
            show-icon
            closable
            style="margin-top:16px"
            @close="error = null"
          />
        </el-card>

        <!-- Results -->
        <template v-if="result">
          <!-- Pipeline visualization -->
          <PipelineViz v-if="result.steps" :steps="result.steps" />

          <!-- Stats cards for this detection -->
          <StatsCards :cards="detectionStatsCards" style="margin-top:20px" />

          <!-- Detection table -->
          <ResultTable v-if="result.detections?.length" :detections="result.detections" />

          <!-- Charts row -->
          <el-row v-if="result.detections?.length" :gutter="16" style="margin-top:20px">
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
        </template>
      </el-col>

      <!-- Right Panel: Recent + Risk + Data Loop -->
      <el-col :xs="24" :md="6">
        <!-- Recent Detections -->
        <el-card shadow="never" style="margin-bottom:16px">
          <template #header>
            <span style="font-weight:600; font-size:15px">最近检测</span>
            <p style="font-size:12px; color:#999; margin-top:2px">最新提交的检测记录</p>
          </template>

          <div v-if="recentItems.length === 0" style="text-align:center; padding:20px; color:#ccc">
            <p>暂无数据</p>
          </div>

          <div v-else class="recent-list">
            <div
              v-for="item in recentItems"
              :key="item.id"
              class="recent-item"
            >
              <div class="recent-info">
                <span class="recent-name">{{ item.filename }}</span>
                <span class="recent-time">{{ formatTime(item.created_at) }}</span>
              </div>
              <el-tag
                v-if="item.risk_level"
                :type="item.risk_level === 'high' ? 'danger' : item.risk_level === 'medium' ? 'warning' : 'success'"
                size="small"
              >
                {{ { high: '高危', medium: '中危', low: '低危' }[item.risk_level] }}
              </el-tag>
            </div>
          </div>
        </el-card>

        <!-- Risk Summary -->
        <RiskSummary style="margin-bottom:16px" />

        <!-- Data Loop -->
        <DataLoop />
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import VChart from 'vue-echarts'
import { detectVisualize, getStats } from '@/api'
import MetricsBar from '@/components/MetricsBar.vue'
import PipelineViz from '@/components/PipelineViz.vue'
import StatsCards from '@/components/StatsCards.vue'
import ResultTable from '@/components/ResultTable.vue'
import RiskSummary from '@/components/RiskSummary.vue'
import DataLoop from '@/components/DataLoop.vue'

// ─── Stats / Recent data ───────────────────────────────────────
const statsData = ref({})
const recentItems = ref([])

async function fetchStats() {
  try {
    const res = await getStats()
    statsData.value = res.data
    recentItems.value = (res.data.recent_detections || []).slice(0, 5)
  } catch (e) { /* silently fail */ }
}

onMounted(fetchStats)

// ─── Detection ──────────────────────────────────────────────────
const selectedFile = ref(null)
const fileList = ref([])
const isProcessing = ref(false)
const result = ref(null)
const error = ref(null)
const progressPct = ref(0)
const progressText = ref('')

function handleFileChange(file) {
  selectedFile.value = file.raw
  result.value = null
  error.value = null
}

function handleRemove() {
  selectedFile.value = null
  result.value = null
  error.value = null
  if (fileList.value.length === 0) {
    selectedFile.value = null
  }
}

async function runDetection() {
  if (!selectedFile.value) return
  isProcessing.value = true
  error.value = null
  result.value = null
  progressPct.value = 30
  progressText.value = '正在检测...'

  try {
    const res = await detectVisualize(selectedFile.value)
    progressPct.value = 100
    progressText.value = '检测完成'
    result.value = res.data
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || '检测失败，请重试'
  } finally {
    isProcessing.value = false
    setTimeout(() => { progressPct.value = 0 }, 1500)
  }
}

function runBatchDetection() {
  // For now, delegates to the dedicated detect page for batch
  // Could be enhanced in a future iteration
}

function scrollToDetect() {
  document.getElementById('detectZone')?.scrollIntoView({ behavior: 'smooth' })
}

// ─── Detection result computed ──────────────────────────────────
const detectionStatsCards = computed(() => {
  if (!result.value) return []
  const r = result.value
  const highCount = r.detections?.filter(d => d.risk_level === 'high').length || 0
  return [
    { label: '检测总数', value: r.detections?.length || 0, sub: '检出藻类个体' },
    { label: '高危预警', value: highCount, sub: '需立即关注', color: highCount ? '#dc2626' : '#16a34a' },
    { label: '质量评分', value: (r.q_score || 0).toFixed(2), sub: 'Q Score', color: r.q_score > 0.7 ? '#16a34a' : '#f59e0b' },
    { label: '处理耗时', value: ((r.processing_time_ms || 0) / 1000).toFixed(1) + 's', sub: '端到端时间' },
    { label: '使用模型', value: 'YOLOv8l', sub: 'FMPD 5类' },
  ]
})

const riskPieOption = computed(() => {
  const dist = { high: 0, medium: 0, low: 0 }
  result.value?.detections?.forEach(d => { if (dist[d.risk_level] !== undefined) dist[d.risk_level]++ })
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
  const names = result.value?.detections?.map(d => d.class_name_zh) || []
  const confs = result.value?.detections?.map(d => +(d.confidence * 100).toFixed(1)) || []
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

function formatTime(ts) {
  if (!ts) return '--'
  return new Date(ts).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
.home-page {
  max-width: 1400px;
  margin: 0 auto;
}

/* ─── Left Panel ─── */
.stat-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-bottom: 20px;
}

.stat-item {
  text-align: center;
  padding: 8px;
  background: #f8fafc;
  border-radius: 8px;
}

.stat-num {
  font-size: 26px;
  font-weight: 700;
  color: #1a3a5c;
}

.stat-text {
  font-size: 12px;
  color: #999;
  margin-top: 2px;
}

.quick-actions {
  border-top: 1px solid #f0f0f0;
  padding-top: 16px;
}

/* ─── Pipeline Mini (Left Panel) ─── */
.pipeline-mini {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 2px;
  font-size: 12px;
}

.pipe-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.pipe-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #2d6a9f;
  color: white;
  font-size: 11px;
  font-weight: 600;
}

.pipe-arrow {
  color: #ccc;
  font-size: 12px;
}

/* ─── Right Panel: Recent List ─── */
.recent-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.recent-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 6px 0;
  border-bottom: 1px solid #f5f5f5;
}

.recent-item:last-child { border-bottom: none; }

.recent-info {
  flex: 1;
  min-width: 0;
}

.recent-name {
  display: block;
  font-size: 13px;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.recent-time {
  font-size: 11px;
  color: #bbb;
}
</style>
