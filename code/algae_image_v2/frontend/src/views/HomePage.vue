<template>
  <div class="dashboard">
    <!-- ═══ Top Bar ═══ -->
    <header class="topbar">
      <div class="brand">
        <div class="brand-mark">微</div>
        <div>
          <h1>微险先知水下微生物监测引领者</h1>
          <p class="subtitle">偏振暗场显微成像 · YOLO识别计数 · 环境因子融合 · <strong>数据闭环</strong></p>
        </div>
      </div>
      <div class="top-actions">
        <div class="status-pill"><i class="status-dot"></i>系统在线</div>
        <button class="btn btn-secondary" @click="refreshDemoData">刷新模拟数据</button>
        <button class="btn btn-primary" @click="$router.push('/detect')">开始检测</button>
      </div>
    </header>

    <!-- ═══ Pipeline Bar ═══ -->
    <div class="pipeline-bar">
      <div class="pipe-step active"><span class="num">1</span><div class="info"><strong>偏振暗场采集</strong><small>DoFP相机 · 多角度</small></div></div>
      <span class="pipe-arrow">→</span>
      <div class="pipe-step active"><span class="num">2</span><div class="info"><strong>Stokes重建</strong><small>S₀ / S₁ / S₂ · RDN</small></div></div>
      <span class="pipe-arrow">→</span>
      <div class="pipe-step active"><span class="num">3</span><div class="info"><strong>图像增强</strong><small>去散射 · 对比度</small></div></div>
      <span class="pipe-arrow">→</span>
      <div class="pipe-step active"><span class="num">4</span><div class="info"><strong>YOLO识别计数</strong><small>分类 · 框选 · 浓度</small></div></div>
      <span class="pipe-arrow">→</span>
      <div class="pipe-step active"><span class="num">5</span><div class="info"><strong>融合预警</strong><small>环境因子 · 四级预警</small></div></div>
    </div>

    <!-- ═══ Metrics ═══ -->
    <section class="metrics">
      <div class="metric"><span>检测总数</span><strong>2,847</strong><small>累计 · 5类FMPD</small></div>
      <div class="metric"><span>今日检测</span><strong>{{ statsData.today_count || 326 }}</strong><small>帧 · 藻种识别</small></div>
      <div class="metric"><span>高危预警</span><strong style="color:#dc2626">{{ statsData.risk_distribution?.high || 170 }}</strong><small>需立即关注</small></div>
      <div class="metric"><span>平均 Q 分</span><strong>0.724</strong><small>图像质量 · 稳定</small></div>
      <div class="metric"><span>有效 FPS</span><strong>2.8</strong><small>处理帧率 · GPU</small></div>
    </section>

    <!-- ═══ Main Layout ═══ -->
    <section class="layout">
      <!-- ── Left: Device Management ── -->
      <aside class="panel">
        <div class="panel-head">
          <div>
            <h2 class="panel-title">设备管理 · 多点位监测</h2>
            <p class="panel-subtitle">点击点位切换实时数据 · 支持扩展为区域网络</p>
          </div>
        </div>
        <div class="site-list">
          <button
            v-for="s in sites"
            :key="s.id"
            class="site-card"
            :class="{ active: activeSite === s.id }"
            @click="activeSite = s.id"
          >
            <div class="site-row">
              <span class="site-name">{{ s.name }}</span>
              <span :class="'risk-badge risk-' + s.risk">{{ riskMap[s.risk].label }}</span>
            </div>
            <div class="site-meta">
              <div>{{ s.scene }} · {{ s.location }}</div>
              <div>检出 {{ s.count }} 个体 · 置信度 {{ s.confidence }}%</div>
            </div>
            <div class="site-trend">
              <span :class="'trend-' + s.trendDir">{{ s.trendDir === 'up' ? '▲' : s.trendDir === 'down' ? '▼' : '─' }} 藻密度趋势</span>
              <span style="margin-left:auto">样本 {{ s.sample }}</span>
            </div>
          </button>
        </div>
      </aside>

      <!-- ── Center: Quick Detection ── -->
      <section class="panel">
        <div class="panel-head">
          <div>
            <h2 class="panel-title">快速检测</h2>
            <p class="panel-subtitle">上传藻类显微图像 · 偏振分析 · YOLO识别 · 管线可视化</p>
          </div>
        </div>

        <div class="monitor">
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
            <el-icon :size="36"><UploadFilled /></el-icon>
            <div style="margin-top:8px; font-size:14px">拖拽或<em>点击上传</em>显微图像</div>
            <template #tip>
              <div style="margin-top:4px; font-size:12px; color:#999">PNG / JPG / TIF / BMP · 最多 50 张</div>
            </template>
          </el-upload>

          <div style="display:flex; gap:10px; justify-content:center; margin-top:12px">
            <el-button type="primary" size="large" :loading="isProcessing" :disabled="!selectedFile" @click="runDetection">
              {{ isProcessing ? '检测中...' : '单图检测' }}
            </el-button>
            <el-button size="large" :disabled="fileList.length < 2" @click="runBatchDetection">批量处理</el-button>
          </div>

          <p v-if="fileList.length" style="text-align:center; font-size:12px; color:#999; margin-top:6px">已选择 {{ fileList.length }} 个文件</p>

          <div v-if="isProcessing" style="margin-top:14px">
            <el-progress :percentage="progressPct" :stroke-width="8" />
            <p style="text-align:center; font-size:12px; color:#999; margin-top:4px">{{ progressText }}</p>
          </div>

          <el-alert v-if="error" :title="error" type="error" show-icon closable style="margin-top:14px" @close="error = null" />

          <template v-if="result">
            <PipelineViz v-if="result.steps" :steps="result.steps" style="margin-top:16px" />
            <ResultTable v-if="result.detections?.length" :detections="result.detections" />
          </template>

          <!-- Species result table (demo when no real result) -->
          <div v-if="!result" class="split" style="margin-top:16px">
            <div>
              <div class="panel-head" style="padding:12px 0 0">
                <div>
                  <h2 class="panel-title">藻种识别结果</h2>
                  <p class="panel-subtitle">YOLO检测输出 · 类别 · 数量 · 置信度</p>
                </div>
              </div>
              <table>
                <thead><tr><th>藻种</th><th>数量</th><th>占比</th><th>置信度</th><th>浓度风险</th></tr></thead>
                <tbody>
                  <tr v-for="sp in currentSiteData.species" :key="sp[0]">
                    <td>{{ sp[0] }}</td><td>{{ sp[1] }}</td><td>{{ sp[2] }}</td><td>{{ sp[3] }}%</td>
                    <td><span :class="'risk-badge risk-' + sp[4]">{{ riskMap[sp[4]].label }}</span></td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div>
              <div class="panel-head" style="padding:12px 0 0">
                <div>
                  <h2 class="panel-title">数据汇流</h2>
                  <p class="panel-subtitle">环境因子 + 生物趋势</p>
                </div>
              </div>
              <div class="chart">
                <svg viewBox="0 0 320 180" preserveAspectRatio="none">
                  <!-- Grid -->
                  <line v-for="i in 5" :key="'h'+i" :x1="0" :y1="i*36" :x2="320" :y2="i*36" stroke="rgba(25,118,210,.06)" stroke-width="1"/>
                  <!-- Temperature (blue) -->
                  <polyline :points="tempPoints" fill="none" stroke="#1976d2" stroke-width="2.5"/>
                  <!-- Chlorophyll (cyan) -->
                  <polyline :points="chloroPoints" fill="none" stroke="#0891b2" stroke-width="2"/>
                  <!-- Turbidity (orange) -->
                  <polyline :points="turbPoints" fill="none" stroke="#ea580c" stroke-width="1.5" stroke-dasharray="4,3"/>
                  <!-- DO (purple) -->
                  <polyline :points="doPoints" fill="none" stroke="#a78bfa" stroke-width="1.5"/>
                </svg>
              </div>
              <div class="chart-labels"><span>00:00</span><span>06:00</span><span>12:00</span><span>18:00</span><span>24:00</span></div>
              <div class="legend">
                <span><i style="background:#1976d2"></i>水温</span>
                <span><i style="background:#0891b2"></i>叶绿素</span>
                <span><i style="background:#ea580c"></i>浊度</span>
                <span><i style="background:#a78bfa"></i>溶解氧</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- ── Right Stack ── -->
      <aside class="right-stack">
        <!-- Ops Status -->
        <section class="panel">
          <div class="panel-head">
            <div>
              <h2 class="panel-title">运维状态</h2>
              <p class="panel-subtitle">设备健康 · 维护提示</p>
            </div>
          </div>
          <div class="ops-list">
            <div class="ops-item" v-for="op in currentSiteData.opsEntries" :key="op[0]">
              <span>{{ op[0] }}</span>
              <div class="bar"><i :style="{ width: op[1] + '%' }"></i></div>
              <span>{{ op[1] }}%</span>
            </div>
          </div>
        </section>

        <!-- Alarms -->
        <section class="panel">
          <div class="panel-head">
            <div>
              <h2 class="panel-title">风险预警 · 历史报警</h2>
              <p class="panel-subtitle">按风险等级筛选 · 含处置建议</p>
            </div>
          </div>
          <div class="risk-filters">
            <button v-for="r in ['all','red','orange','yellow','green']" :key="r"
              class="risk-filter" :class="{ active: activeRisk === r }" @click="activeRisk = r">
              {{ r === 'all' ? '全部' : riskMap[r].text }}
            </button>
          </div>
          <div class="alarm-list">
            <div class="alarm-item" v-for="a in filteredAlarms" :key="a.id">
              <div class="alarm-main">
                <strong>{{ a.site }}</strong>
                <span>{{ a.desc }}</span>
                <div class="alarm-suggest">{{ a.suggest }}</div>
              </div>
              <span :class="'risk-badge risk-' + a.risk">{{ riskMap[a.risk].label }}</span>
            </div>
          </div>
        </section>

        <!-- Data Loop -->
        <section class="panel">
          <div class="panel-head">
            <div>
              <h2 class="panel-title">数据闭环</h2>
              <p class="panel-subtitle">采集 → 识别 → 复核 → 再训练</p>
            </div>
          </div>
          <div class="loop-flow">
            <div class="loop-node done"><span class="dot">1</span><label>偏振采集</label></div>
            <div class="loop-node done"><span class="dot">2</span><label>RDN重建</label></div>
            <div class="loop-node done"><span class="dot">3</span><label>YOLO识别</label></div>
            <div class="loop-node done"><span class="dot">4</span><label>人工复核</label></div>
            <div class="loop-node"><span class="dot">5</span><label>加入训练</label></div>
            <div class="loop-node"><span class="dot">6</span><label>模型升级</label></div>
          </div>
          <div class="loop-stats">
            <span>已完成 <strong>1,248</strong> 条复核</span>
            <span>训练池 <strong>{{ trainingPool }}</strong> 张</span>
          </div>
          <div class="loop-list">
            <div class="loop-item done" v-for="li in loopItems" :key="li.id">
              <div class="loop-step">
                <span class="step-dot">✓</span>
                <span>{{ li.filename }}</span>
              </div>
              <span class="risk-badge risk-green">已复核</span>
            </div>
          </div>
          <div class="footer-actions">
            <button class="btn btn-primary" @click="$router.push('/review')">人工复核</button>
            <button class="btn btn-secondary" @click="$router.push('/review')">加入训练集</button>
          </div>
          <div class="network-badge">
            <i class="net-dot"></i>
            <span>区域监测网络 · <strong class="net-count">{{ sites.filter(s => s.status === 'online').length }}</strong> 个在线节点 · 支持扩展至 <strong>N</strong> 个点位</span>
          </div>
        </section>
      </aside>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { detectVisualize, getStats, getDevices } from '@/api'
import PipelineViz from '@/components/PipelineViz.vue'
import ResultTable from '@/components/ResultTable.vue'

// ─── Risk Map ─────────────────────────────────────────────────────
const riskMap = {
  green: { text: '绿色', label: '低风险' },
  yellow: { text: '黄色', label: '注意' },
  orange: { text: '橙色', label: '预警' },
  red: { text: '红色', label: '高风险' },
}

// ─── Demo Device Data ─────────────────────────────────────────────
const activeSite = ref('AQ-01')
const sites = ref([
  {
    id: 'AQ-01', name: '海洋牧场养殖池 A1', scene: '水产养殖', location: '近岸示范区 · 2.1m',
    risk: 'orange', count: 1247, confidence: 89, sample: 142, trendDir: 'up', status: 'online',
    ops: { 相机模组: 96, 光源: 91, 网络: 88, 供电: 82, 窗口清洁: 72 },
    species: [
      ['球形棕囊藻', 487, '39%', 91, 'red'],
      ['微囊藻', 312, '25%', 87, 'orange'],
      ['小球藻', 268, '21%', 82, 'green'],
      ['直链藻', 180, '14%', 79, 'yellow'],
    ],
  },
  {
    id: 'RS-03', name: '水库取水口 3号', scene: '水源地', location: '岸基旁路 · 1.4m',
    risk: 'yellow', count: 642, confidence: 84, sample: 98, trendDir: 'flat', status: 'online',
    ops: { 相机模组: 94, 光源: 89, 网络: 91, 供电: 88, 窗口清洁: 66 },
    species: [
      ['微囊藻', 218, '34%', 87, 'orange'],
      ['小球藻', 175, '27%', 81, 'green'],
      ['栅藻', 156, '24%', 76, 'yellow'],
      ['直链藻', 93, '14%', 74, 'green'],
    ],
  },
  {
    id: 'LK-07', name: '景观湖监测浮标 7号', scene: '城市景观', location: '湖心浮标 · 1.8m',
    risk: 'green', count: 104, confidence: 79, sample: 56, trendDir: 'down', status: 'online',
    ops: { 相机模组: 78, 光源: 81, 网络: 85, 供电: 62, 窗口清洁: 58 },
    species: [
      ['小球藻', 52, '50%', 82, 'green'],
      ['直链藻', 30, '29%', 76, 'green'],
      ['栅藻', 15, '14%', 71, 'yellow'],
      ['其他藻种', 7, '7%', 68, 'green'],
    ],
  },
])

const currentSiteData = computed(() => {
  const s = sites.value.find(s => s.id === activeSite.value) || sites.value[0]
  return {
    ...s,
    opsEntries: Object.entries(s.ops),
  }
})

// ─── Demo Chart Data ──────────────────────────────────────────────
const envData = { temp: [24, 25, 26, 28, 29, 29, 28], chloro: [18, 20, 25, 28, 32, 36, 33], turb: [12, 13, 15, 17, 18, 20, 17], doxy: [7.2, 6.8, 6.3, 6.0, 5.9, 5.7, 6.1] }
function envToPoints(arr, max, h) {
  const step = 320 / (arr.length - 1)
  return arr.map((v, i) => `${i * step},${h - (v / max) * h}`).join(' ')
}
const tempPoints = computed(() => envToPoints(envData.temp, 36, 160))
const chloroPoints = computed(() => envToPoints(envData.chloro, 40, 160))
const turbPoints = computed(() => envToPoints(envData.turb, 25, 160))
const doPoints = computed(() => envToPoints(envData.doxy, 10, 160))

// ─── Alarms (demo) ────────────────────────────────────────────────
const activeRisk = ref('all')
const alarms = ref([
  { id: 1, site: '养殖池 A1', desc: '球形棕囊藻密度急剧上升 · 24h增幅 38%', suggest: '建议现场确认并准备处置', risk: 'orange' },
  { id: 2, site: '取水口 3号', desc: '微囊藻检出数持续偏高 · 连续超标', suggest: '提醒复核，增加采样频率', risk: 'yellow' },
  { id: 3, site: '养殖池 A1', desc: 'DoLP信噪比下降 · 光源老化？', suggest: '建议现场检查光源寿命', risk: 'yellow' },
  { id: 4, site: '浮标 7号', desc: '窗口透过率衰减 · 需清洗维护', suggest: '正常监测，记录基线', risk: 'green' },
])
const filteredAlarms = computed(() => activeRisk.value === 'all' ? alarms.value : alarms.value.filter(a => a.risk === activeRisk.value))

// ─── Data Loop (demo) ─────────────────────────────────────────────
const trainingPool = ref(293)
const loopItems = ref([
  { id: 1, filename: 'SNAP-003217-0030.tif' },
  { id: 2, filename: 'SNAP-003217-0056.tif' },
  { id: 3, filename: 'SNAP-003217-0089.tif' },
])

// ─── Device Management (real API + demo fallback) ──────────────────
async function fetchDevices() {
  try {
    const res = await getDevices()
    const list = res.data.devices || []
    if (list.length) {
      sites.value = list.map(d => ({
        id: d.id, name: d.name, scene: d.location, location: d.model,
        risk: d.alerts > 0 ? (d.alerts > 5 ? 'orange' : 'yellow') : 'green',
        count: d.today_frames, confidence: 89, sample: 0,
        trendDir: 'flat', status: d.status,
        ops: { 相机模组: d.status === 'online' ? 96 : 0, 光源: 91, 网络: 88, 供电: 82, 窗口清洁: 72 },
        species: [['检测中', 0, '--', 0, 'green']],
      }))
    }
  } catch (_) { /* keep demo data */ }
}

// ─── Stats / Detection ────────────────────────────────────────────
const statsData = ref({})
async function fetchStats() {
  try { const res = await getStats(); statsData.value = res.data } catch (_) {}
}
onMounted(() => { fetchStats(); fetchDevices() })

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
    progressPct.value = 100; progressText.value = '检测完成'; result.value = res.data
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || '检测失败'
  } finally {
    isProcessing.value = false
    setTimeout(() => { progressPct.value = 0 }, 1500)
  }
}
function runBatchDetection() {}
function refreshDemoData() {
  // Animate a quick refresh feel
}
</script>

<style scoped>
/* ═══ Root Tokens ═══ */
.dashboard {
  --bg: #f4f8fc;
  --panel: #ffffff;
  --panel-2: #f7fbff;
  --line: #d8e5f2;
  --line-soft: rgba(15, 40, 70, .08);
  --text: #162235;
  --muted: #65778b;
  --blue: #1976d2;
  --cyan: #0891b2;
  --green: #16a34a;
  --yellow: #ca8a04;
  --orange: #ea580c;
  --red: #dc2626;
  --shadow: 0 18px 46px rgba(28, 74, 121, .12);
  max-width: 1440px;
  margin: 0 auto;
  padding: 18px 0 28px;
  font-family: "Microsoft YaHei", "PingFang SC", Arial, sans-serif;
  color: var(--text);
}

/* ═══ Top Bar ═══ */
.topbar { display: flex; align-items: center; justify-content: space-between; min-height: 68px; padding: 0 6px; gap: 18px; }
.brand { display: flex; align-items: center; gap: 14px; min-width: 0; }
.brand-mark {
  width: 42px; height: 42px; display: grid; place-items: center;
  border: 1px solid rgba(67, 183, 255, .6);
  background: linear-gradient(145deg, rgba(67,183,255,.2), rgba(57,215,200,.12));
  border-radius: 8px; box-shadow: inset 0 0 18px rgba(25,118,210,.16);
  color: var(--blue); font-weight: 800; font-size: 20px;
}
.brand h1 { margin: 0; font-size: clamp(22px, 2vw, 30px); line-height: 1.1; color: #000; }
.subtitle { margin: 5px 0 0; color: var(--muted); font-size: 13px; }
.subtitle strong { color: var(--blue); font-weight: 600; }
.top-actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }

.status-pill, .btn {
  height: 36px; border-radius: 8px; border: 1px solid var(--line);
  color: var(--text); background: rgba(255,255,255,.86);
  display: inline-flex; align-items: center; gap: 8px; padding: 0 12px; white-space: nowrap; font-size: 13px;
}
.status-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--green); box-shadow: 0 0 12px rgba(22,163,74,.35); }
.btn-primary { background: linear-gradient(180deg, rgba(25,118,210,.12), rgba(25,118,210,.06)); border-color: rgba(25,118,210,.34); }
.btn-primary:hover, .btn-secondary:hover { border-color: rgba(25,118,210,.7); transform: translateY(-1px); }

/* ═══ Pipeline Bar ═══ */
.pipeline-bar { display: flex; align-items: center; gap: 2px; margin-top: 14px; padding: 10px 16px; background: linear-gradient(180deg, rgba(255,255,255,.96), rgba(247,251,255,.96)); border: 1px solid var(--line); border-radius: 8px; box-shadow: var(--shadow); overflow-x: auto; }
.pipe-step { display: flex; align-items: center; gap: 8px; flex: 1; min-width: 0; }
.pipe-step .num { width: 26px; height: 26px; border-radius: 50%; display: grid; place-items: center; font-size: 12px; font-weight: 800; background: rgba(15,40,70,.06); color: var(--muted); flex-shrink: 0; }
.pipe-step.active .num { background: linear-gradient(135deg, var(--blue), var(--cyan)); color: #fff; box-shadow: 0 0 16px rgba(25,118,210,.35); }
.pipe-step .info strong { display: block; font-size: 13px; line-height: 1.2; }
.pipe-step .info small { color: var(--muted); font-size: 11px; }
.pipe-arrow { color: #c8d6e5; font-size: 18px; flex-shrink: 0; margin: 0 2px; }

/* ═══ Metrics ═══ */
.metrics { display: grid; grid-template-columns: repeat(5, minmax(0,1fr)); gap: 12px; margin-top: 12px; }
.metric { min-height: 94px; border-radius: 8px; padding: 15px 16px; position: relative; overflow: hidden; background: linear-gradient(180deg, rgba(255,255,255,.98), rgba(247,251,255,.98)); border: 1px solid var(--line); box-shadow: var(--shadow); }
.metric::after { content: ""; position: absolute; inset: auto 14px 0 14px; height: 2px; background: linear-gradient(90deg, transparent, rgba(25,118,210,.42), transparent); opacity: .5; }
.metric span { display: block; color: var(--muted); font-size: 13px; }
.metric strong { display: block; margin-top: 8px; font-size: 28px; letter-spacing: 0; }
.metric small { color: var(--muted); font-size: 12px; }

/* ═══ Layout ═══ */
.layout { display: grid; grid-template-columns: 300px minmax(0,1fr) 340px; gap: 14px; margin-top: 14px; }
.panel { border-radius: 8px; min-width: 0; background: linear-gradient(180deg, rgba(255,255,255,.98), rgba(247,251,255,.98)); border: 1px solid var(--line); box-shadow: var(--shadow); }
.panel-head { min-height: 54px; padding: 14px 16px 0; display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.panel-title { margin: 0; font-size: 14px; font-weight: 700; }
.panel-subtitle { margin: 5px 0 0; color: var(--muted); font-size: 12px; }

/* ═══ Site Cards ═══ */
.site-list { padding: 10px; display: grid; gap: 10px; }
.site-card { width: 100%; text-align: left; color: var(--text); border-radius: 8px; padding: 12px; border: 1px solid var(--line); background: linear-gradient(180deg, rgba(255,255,255,.98), rgba(247,251,255,.98)); transition: .18s ease; font: inherit; cursor: pointer; }
.site-card:hover, .site-card.active { border-color: rgba(25,118,210,.72); background: linear-gradient(180deg, rgba(25,118,210,.1), rgba(255,255,255,.98)); }
.site-row { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.site-name { font-weight: 700; font-size: 14px; }
.site-meta { margin-top: 8px; color: var(--muted); font-size: 12px; line-height: 1.6; }
.site-trend { display: flex; align-items: center; gap: 4px; margin-top: 6px; font-size: 12px; }
.trend-up { color: var(--red); }
.trend-down { color: var(--green); }
.trend-flat { color: var(--muted); }

/* ═══ Risk Badges ═══ */
.risk-badge { display: inline-flex; align-items: center; justify-content: center; min-width: 56px; height: 24px; padding: 0 9px; border-radius: 7px; border: 1px solid currentColor; font-size: 12px; font-weight: 700; }
.risk-green { color: var(--green); background: rgba(74,222,128,.1); }
.risk-yellow { color: var(--yellow); background: rgba(250,204,21,.1); }
.risk-orange { color: var(--orange); background: rgba(251,146,60,.1); }
.risk-red { color: var(--red); background: rgba(251,78,93,.12); }

/* ═══ Monitor / Center ═══ */
.monitor { padding: 14px 16px 16px; }

/* ═══ Table ═══ */
.split { display: grid; grid-template-columns: 1.1fr .9fr; gap: 14px; margin-top: 14px; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { padding: 11px 8px; border-bottom: 1px solid var(--line-soft); text-align: left; white-space: nowrap; }
th { color: var(--muted); font-weight: 500; }

/* ═══ Chart ═══ */
.chart { height: 220px; padding: 12px 10px 8px; border: 1px solid var(--line); border-radius: 8px; background: linear-gradient(rgba(25,118,210,.08) 1px, transparent 1px), linear-gradient(90deg, rgba(25,118,210,.08) 1px, transparent 1px), rgba(247,251,255,.74); background-size: 100% 25%, 14.2% 100%, auto; }
.chart svg { width: 100%; height: 100%; display: block; }
.chart-labels { display: grid; grid-template-columns: repeat(5,1fr); gap: 6px; margin-top: 10px; font-size: 12px; color: var(--muted); }
.legend { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; color: var(--muted); font-size: 12px; }
.legend i { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 5px; vertical-align: -1px; }

/* ═══ Right Stack ═══ */
.right-stack { display: grid; gap: 14px; }
.ops-list, .loop-list, .alarm-list { padding: 10px 16px 16px; display: grid; gap: 10px; }
.ops-item, .loop-item, .alarm-item { display: flex; align-items: center; justify-content: space-between; gap: 12px; border: 1px solid var(--line-soft); border-radius: 8px; padding: 10px; background: rgba(247,251,255,.72); font-size: 13px; }
.bar { width: 96px; height: 8px; overflow: hidden; border-radius: 999px; background: rgba(25,118,210,.12); }
.bar > i { display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, var(--cyan), var(--blue)); }
.risk-filters { display: flex; flex-wrap: wrap; gap: 8px; padding: 0 16px 8px; }
.risk-filter { height: 34px; padding: 0 12px; color: var(--muted); border: 1px solid var(--line); border-radius: 8px; background: rgba(247,251,255,.86); transition: .18s ease; font: inherit; cursor: pointer; }
.risk-filter.active { color: var(--text); border-color: rgba(25,118,210,.72); background: rgba(25,118,210,.1); }
.alarm-item { align-items: flex-start; }
.alarm-main strong { display: block; margin-bottom: 4px; font-size: 13px; }
.alarm-main span { color: var(--muted); font-size: 12px; line-height: 1.5; }
.alarm-suggest { margin-top: 6px; padding: 4px 8px; border-radius: 5px; font-size: 11px; background: rgba(25,118,210,.06); border: 1px solid var(--line-soft); color: var(--muted); }

/* ═══ Data Loop ═══ */
.loop-flow { padding: 10px 16px 4px; display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.loop-node { display: flex; flex-direction: column; align-items: center; gap: 4px; padding: 10px 6px; border: 1px solid var(--line-soft); border-radius: 8px; background: rgba(247,251,255,.72); text-align: center; font-size: 12px; }
.loop-node .dot { width: 28px; height: 28px; border-radius: 50%; display: grid; place-items: center; font-size: 14px; font-weight: 800; background: var(--line-soft); color: var(--muted); }
.loop-node.done .dot { background: var(--green); color: #fff; }
.loop-node label { font-weight: 600; font-size: 13px; }
.loop-stats { padding: 4px 16px 10px; display: flex; gap: 12px; font-size: 12px; color: var(--muted); justify-content: center; }
.loop-stats strong { color: var(--text); }
.loop-item.done { border-color: rgba(74,222,128,.35); }
.loop-step { display: flex; align-items: center; gap: 9px; }
.step-dot { width: 20px; height: 20px; display: grid; place-items: center; border-radius: 50%; color: #07111d; background: var(--green); font-size: 12px; font-weight: 800; }
.footer-actions { display: flex; gap: 10px; padding: 0 16px 16px; }
.btn-secondary { background: rgba(255,255,255,.92); border-color: var(--line); }
.network-badge { margin: 0 16px 12px; padding: 10px 12px; border-radius: 8px; border: 1px solid rgba(25,118,210,.2); background: rgba(25,118,210,.04); display: flex; align-items: center; gap: 10px; font-size: 12px; }
.net-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--green); box-shadow: 0 0 8px rgba(22,163,74,.3); }
.net-count { font-weight: 700; color: var(--blue); }

/* ═══ Override Element Plus ═══ */
.upload-zone :deep(.el-upload-dragger) { background: linear-gradient(180deg, rgba(247,251,255,.8), rgba(255,255,255,.8)); border: 2px dashed var(--line); border-radius: 8px; }

/* ═══ Responsive ═══ */
@media (max-width: 1200px) { .metrics { grid-template-columns: repeat(3, minmax(0,1fr)); } .layout { grid-template-columns: 280px minmax(0,1fr); } .right-stack { grid-column: 1 / -1; grid-template-columns: repeat(3, minmax(0,1fr)); } }
@media (max-width: 900px) { .metrics, .layout, .split, .right-stack { grid-template-columns: 1fr; } .topbar { flex-direction: column; align-items: flex-start; } .loop-flow { grid-template-columns: 1fr 1fr; } }
</style>
