<template>
  <div class="home-dashboard">
    <!-- ═══ Metrics Bar ═══ -->
    <MetricsBar />

    <!-- ═══ Pipeline Visualization ═══ -->
    <div class="pipeline-bar">
      <div class="pipe-step active">
        <span class="num">1</span>
        <div class="info"><strong>偏振采集</strong><small>DoFP相机 · I₀ I₄₅ I₉₀</small></div>
      </div>
      <span class="arrow">▸</span>
      <div class="pipe-step active">
        <span class="num">2</span>
        <div class="info"><strong>偏振模拟</strong><small>结构张量 · Malus定律</small></div>
      </div>
      <span class="arrow">▸</span>
      <div class="pipe-step active">
        <span class="num">3</span>
        <div class="info"><strong>RDN 重建</strong><small>PSNR 62.46dB · 12 RDB</small></div>
      </div>
      <span class="arrow">▸</span>
      <div class="pipe-step active">
        <span class="num">4</span>
        <div class="info"><strong>I<sub>enh</sub> 增强</strong><small>S₀(1+α−γ·DoLP+β·|sin 2AoP|·DoLP)</small></div>
      </div>
      <span class="arrow">▸</span>
      <div class="pipe-step active">
        <span class="num">5</span>
        <div class="info"><strong>YOLO 识别</strong><small>YOLOv8s · FMPD 5类</small></div>
      </div>
    </div>

    <!-- ═══ Main Grid ═══ -->
    <div class="main-grid">
      <!-- ── Left: Device Management ── -->
      <div class="panel">
        <div class="panel-head">
          <h2 class="panel-title">设备管理 · 多点位监测</h2>
          <p class="panel-sub">在线设备 · 实时状态</p>
        </div>
        <div class="device-list">
          <div
            v-for="d in devices"
            :key="d.id"
            class="device-card"
            :class="{ active: d.active }"
            @click="activeDevice = d.id"
          >
            <div class="dev-top">
              <span class="dev-dot" :class="d.status"></span>
              <span class="dev-name">{{ d.name }}</span>
              <el-tag :type="d.status === 'online' ? 'success' : 'info'" size="small" effect="light">
                {{ d.status === 'online' ? '在线' : '离线' }}
              </el-tag>
            </div>
            <div class="dev-meta">
              <span>{{ d.location }}</span>
              <span>{{ d.model }}</span>
            </div>
            <div class="dev-stats">
              <div class="dev-stat">
                <strong>{{ d.todayFrames }}</strong>
                <small>今日帧</small>
              </div>
              <div class="dev-stat">
                <strong :style="{ color: d.alerts ? '#dc2626' : '#16a34a' }">{{ d.alerts }}</strong>
                <small>预警</small>
              </div>
              <div class="dev-stat">
                <strong>{{ d.uptime }}</strong>
                <small>运行</small>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ── Center: Quick Detection ── -->
      <div class="panel" id="detectZone">
        <div class="panel-head">
          <h2 class="panel-title">快速检测</h2>
          <p class="panel-sub">上传显微图像 · 偏振分析 · AI识别</p>
        </div>

        <el-upload
          ref="uploadRef"
          drag
          :auto-upload="false"
          :limit="50"
          accept="image/*"
          :on-change="handleFileChange"
          :on-remove="handleRemove"
          :file-list="fileList"
          class="upload-zone"
        >
          <el-icon :size="40"><UploadFilled /></el-icon>
          <div style="margin-top:10px; font-size:14px">拖拽或<em>点击上传</em>显微图像</div>
          <template #tip>
            <div style="margin-top:6px; font-size:12px; color:#999">PNG / JPG / TIF / BMP · 最多 50 张</div>
          </template>
        </el-upload>

        <div style="display:flex; gap:10px; justify-content:center; margin-top:14px">
          <el-button type="primary" size="large" :loading="isProcessing" :disabled="!selectedFile" @click="runDetection">
            {{ isProcessing ? '检测中...' : '单图检测' }}
          </el-button>
          <el-button size="large" :disabled="fileList.length < 2" @click="runBatchDetection">批量处理</el-button>
        </div>

        <p v-if="fileList.length" style="text-align:center; font-size:12px; color:#999; margin-top:6px">
          已选择 {{ fileList.length }} 个文件
        </p>

        <!-- Progress -->
        <div v-if="isProcessing" style="margin-top:14px">
          <el-progress :percentage="progressPct" :stroke-width="8" />
          <p style="text-align:center; font-size:12px; color:#999; margin-top:4px">{{ progressText }}</p>
        </div>

        <el-alert v-if="error" :title="error" type="error" show-icon closable style="margin-top:14px" @close="error = null" />

        <!-- Results -->
        <template v-if="result">
          <PipelineViz v-if="result.steps" :steps="result.steps" style="margin-top:16px" />
          <StatsCards :cards="detectionStatsCards" style="margin-top:16px" />
          <ResultTable v-if="result.detections?.length" :detections="result.detections" style="margin-top:16px" />
        </template>
      </div>

      <!-- ── Right: Data Analysis ── -->
      <div class="right-stack">
        <!-- Risk Summary -->
        <div class="panel">
          <div class="panel-head">
            <h2 class="panel-title">风险概览</h2>
            <p class="panel-sub">FMPD 5类 · 实时统计</p>
          </div>
          <v-chart v-if="riskPieReady" :option="riskPieOption" style="height:220px" autoresize />
          <div v-else style="height:220px; display:flex; align-items:center; justify-content:center; color:#ccc">
            暂无数据
          </div>
        </div>

        <!-- Detection Trend -->
        <div class="panel" style="margin-top:14px">
          <div class="panel-head">
            <h2 class="panel-title">检测趋势</h2>
            <p class="panel-sub">近 24 小时 · 按小时聚合</p>
          </div>
          <v-chart v-if="trendReady" :option="trendOption" style="height:200px" autoresize />
          <div v-else style="height:200px; display:flex; align-items:center; justify-content:center; color:#ccc">
            暂无数据
          </div>
        </div>

        <!-- Recent History -->
        <div class="panel" style="margin-top:14px">
          <div class="panel-head">
            <h2 class="panel-title">最近记录</h2>
            <p class="panel-sub">最新检测提交</p>
          </div>
          <div v-if="recentItems.length === 0" style="text-align:center; padding:20px; color:#ccc">暂无数据</div>
          <div v-else class="recent-list">
            <div v-for="item in recentItems" :key="item.id" class="recent-item">
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
        </div>
      </div>
    </div>
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

// ─── Device Management (mock data for presentation) ────────────────
const activeDevice = ref(1)
const devices = ref([
  { id: 1, name: '主监测点 · 太湖A', location: '无锡 · 梅梁湾', model: 'MV-CA013-20GC', status: 'online', todayFrames: 1247, alerts: 3, uptime: '72h', active: true },
  { id: 2, name: '辅监测点 · 太湖B', location: '苏州 · 东山', model: 'MV-CA013-20GC', status: 'online', todayFrames: 893, alerts: 0, uptime: '48h', active: false },
  { id: 3, name: '移动站 · 快检仪', location: '巡航船载', model: 'MV-CS016-10GC', status: 'offline', todayFrames: 0, alerts: 0, uptime: '--', active: false },
])

// ─── Stats / Recent ──────────────────────────────────────────────
const statsData = ref({})
const recentItems = ref([])

async function fetchStats() {
  try {
    const res = await getStats()
    statsData.value = res.data
    recentItems.value = (res.data.recent_detections || []).slice(0, 6)
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

function handleFileChange(file) { selectedFile.value = file.raw; result.value = null; error.value = null }
function handleRemove() { selectedFile.value = null; result.value = null; error.value = null }

async function runDetection() {
  if (!selectedFile.value) return
  isProcessing.value = true; error.value = null; result.value = null
  progressPct.value = 30; progressText.value = '正在检测...'
  try {
    const res = await detectVisualize(selectedFile.value)
    progressPct.value = 100; progressText.value = '检测完成'
    result.value = res.data
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || '检测失败'
  } finally {
    isProcessing.value = false
    setTimeout(() => { progressPct.value = 0 }, 1500)
  }
}

function runBatchDetection() {}

function scrollToDetect() {
  document.getElementById('detectZone')?.scrollIntoView({ behavior: 'smooth' })
}

// ─── Detection Stats ────────────────────────────────────────────
const detectionStatsCards = computed(() => {
  if (!result.value) return []
  const r = result.value
  return [
    { label: '检出总数', value: r.detections?.length || 0, sub: '藻类个体' },
    { label: '高危预警', value: r.detections?.filter(d => d.risk_level === 'high').length || 0, sub: '需关注', color: (r.detections?.filter(d => d.risk_level === 'high').length || 0) > 0 ? '#dc2626' : '#16a34a' },
    { label: 'Q 评分', value: (r.q_score || 0).toFixed(2), sub: '质量', color: r.q_score > 0.7 ? '#16a34a' : '#f59e0b' },
    { label: '耗时', value: ((r.processing_time_ms || 0) / 1000).toFixed(1) + 's', sub: '端到端' },
    { label: '模型', value: 'YOLOv8s', sub: 'FMPD 5类' },
  ]
})

// ─── Charts ─────────────────────────────────────────────────────
const riskPieReady = computed(() => !!statsData.value.risk_distribution)
const riskPieOption = computed(() => {
  const d = statsData.value.risk_distribution || {}
  return {
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie', radius: ['45%', '72%'],
      label: { show: true, formatter: '{b}: {c}' },
      data: [
        { value: d.high || 0, name: '高危', itemStyle: { color: '#dc2626' } },
        { value: d.medium || 0, name: '中危', itemStyle: { color: '#f59e0b' } },
        { value: d.low || 0, name: '低危', itemStyle: { color: '#16a34a' } },
      ],
    }],
  }
})

const trendReady = ref(true)
const trendOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: ['00:00','04:00','08:00','12:00','16:00','20:00','现在'], axisLabel: { fontSize: 10 } },
  yAxis: { type: 'value', name: '检出数' },
  series: [{
    type: 'line', smooth: true,
    data: [8, 12, 23, 18, 31, 27, 15],
    areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(25,118,210,.18)' }, { offset: 1, color: 'rgba(25,118,210,0)' }] } },
    lineStyle: { color: '#1976d2', width: 2 },
    itemStyle: { color: '#1976d2' },
  }],
  grid: { left: 48, right: 16, top: 16, bottom: 28 },
}))

function formatTime(ts) {
  if (!ts) return '--'
  return new Date(ts).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
/* ── Root Tokens ── */
.home-dashboard {
  --bg: #f4f8fc;
  --panel-bg: linear-gradient(180deg, rgba(255,255,255,.98), rgba(247,251,255,.98));
  --line: #d8e5f2;
  --blue: #1976d2;
  --cyan: #0891b2;
  --shadow: 0 18px 46px rgba(28,74,121,.10);
  --radius: 8px;
  max-width: 1440px;
  margin: 0 auto;
  font-family: "Microsoft YaHei", "PingFang SC", Arial, sans-serif;
}

/* ── Pipeline Bar ── */
.pipeline-bar {
  display: flex;
  align-items: center;
  gap: 2px;
  margin-top: 12px;
  padding: 10px 18px;
  background: var(--panel-bg);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  overflow-x: auto;
}
.pipe-step {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}
.pipe-step .num {
  width: 26px; height: 26px;
  border-radius: 50%;
  display: grid; place-items: center;
  font-size: 12px; font-weight: 800;
  background: rgba(15,40,70,.06);
  color: #65778b;
  flex-shrink: 0;
}
.pipe-step.active .num {
  background: linear-gradient(135deg, var(--blue), var(--cyan));
  color: #fff;
  box-shadow: 0 0 14px rgba(25,118,210,.30);
}
.pipe-step .info strong { display: block; font-size: 12px; line-height: 1.2; }
.pipe-step .info small { color: #65778b; font-size: 10px; }
.pipe-arrow, .arrow { color: #c8d6e5; font-size: 16px; flex-shrink: 0; }

/* ── Main Grid ── */
.main-grid {
  display: grid;
  grid-template-columns: 280px 1fr 320px;
  gap: 14px;
  margin-top: 14px;
  align-items: start;
}
@media (max-width: 1200px) {
  .main-grid { grid-template-columns: 1fr; }
}

/* ── Panel ── */
.panel {
  background: var(--panel-bg);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 16px;
}
.panel-head { margin-bottom: 12px; }
.panel-title { margin: 0; font-size: 15px; font-weight: 600; letter-spacing: 0; }
.panel-sub { margin: 2px 0 0; color: #65778b; font-size: 12px; }

/* ── Device List ── */
.device-list { display: flex; flex-direction: column; gap: 10px; }
.device-card {
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 6px;
  cursor: pointer;
  transition: .15s;
}
.device-card:hover, .device-card.active { border-color: rgba(25,118,210,.4); background: rgba(25,118,210,.03); }
.dev-top { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.dev-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.dev-dot.online { background: #16a34a; box-shadow: 0 0 8px rgba(22,163,74,.4); }
.dev-dot.offline { background: #ccc; }
.dev-name { font-size: 13px; font-weight: 600; flex: 1; }
.dev-meta { display: flex; gap: 12px; font-size: 11px; color: #999; margin-bottom: 8px; }
.dev-stats { display: flex; gap: 16px; }
.dev-stat { text-align: center; }
.dev-stat strong { display: block; font-size: 16px; }
.dev-stat small { font-size: 10px; color: #999; }

/* ── Upload ── */
.upload-zone :deep(.el-upload-dragger) {
  background: linear-gradient(180deg, rgba(247,251,255,.8), rgba(255,255,255,.8));
  border: 2px dashed var(--line);
  border-radius: var(--radius);
}

/* ── Recent List ── */
.recent-list { display: flex; flex-direction: column; gap: 8px; }
.recent-item { display: flex; align-items: center; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid rgba(15,40,70,.06); }
.recent-item:last-child { border-bottom: none; }
.recent-info { flex: 1; min-width: 0; }
.recent-name { display: block; font-size: 12px; color: #333; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.recent-time { font-size: 10px; color: #bbb; }

/* ── Override Element Plus card shadows for consistency ── */
:deep(.el-card) { box-shadow: var(--shadow) !important; border: 1px solid var(--line) !important; }
</style>
