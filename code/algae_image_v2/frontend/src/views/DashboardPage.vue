<template>
  <div class="dashboard-page" style="max-width:1000px; margin:0 auto">
    <!-- Stats cards -->
    <StatsCards :cards="statsCards" style="margin-bottom:20px" />

    <!-- Charts row -->
    <el-row :gutter="16">
      <el-col :xs="24" :md="12">
        <el-card shadow="never" style="margin-bottom:16px">
          <template #header>藻种分布</template>
          <v-chart :option="classPieOption" style="height:300px" autoresize />
        </el-card>
      </el-col>
      <el-col :xs="24" :md="12">
        <el-card shadow="never" style="margin-bottom:16px">
          <template #header>风险等级分布</template>
          <v-chart :option="riskBarOption" style="height:300px" autoresize />
        </el-card>
      </el-col>
    </el-row>

    <!-- Recent detections -->
    <el-card shadow="never">
      <template #header>最近检测</template>
      <el-table :data="recent" stripe size="small" empty-text="暂无数据">
        <el-table-column prop="filename" label="文件名" min-width="160" />
        <el-table-column prop="risk_level" label="风险" width="80">
          <template #default="{ row }">
            <el-tag
              v-if="row.risk_level"
              :type="row.risk_level === 'high' ? 'danger' : row.risk_level === 'medium' ? 'warning' : 'success'"
              size="small"
            >
              {{ { high: '高', medium: '中', low: '低' }[row.risk_level] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="q_score" label="质量分" width="80">
          <template #default="{ row }">{{ row.q_score?.toFixed(2) || '--' }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="170" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import VChart from 'vue-echarts'
import { getStats } from '@/api'
import StatsCards from '@/components/StatsCards.vue'

const stats = ref(null)
const recent = ref([])

async function fetchStats() {
  try {
    const res = await getStats()
    stats.value = res.data
    recent.value = res.data.recent_detections || []
  } catch (e) { /* silently fail */ }
}

const statsCards = computed(() => {
  if (!stats.value) return []
  const s = stats.value
  const highCount = s.risk_distribution?.high || 0
  return [
    { label: '总检测次数', value: s.total_detections, sub: '累计检测样本' },
    { label: '今日检测', value: s.today_count, sub: '当日处理量' },
    { label: '高危预警', value: highCount, sub: '需立即关注', color: highCount ? '#dc2626' : '#16a34a' },
    { label: '活跃藻种', value: Object.keys(s.class_distribution || {}).length, sub: '检出类别数' },
  ]
})

const classPieOption = computed(() => {
  const dist = stats.value?.class_distribution || {}
  const data = Object.entries(dist).map(([name, value]) => ({ name, value }))
  return {
    tooltip: { trigger: 'item' },
    legend: { type: 'scroll', bottom: 0 },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['50%', '45%'],
      data,
      label: { formatter: '{b}: {c}' },
    }],
  }
})

const riskBarOption = computed(() => {
  const dist = stats.value?.risk_distribution || {}
  return {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: ['高危', '中危', '低危'] },
    yAxis: { type: 'value', name: '数量' },
    series: [{
      type: 'bar',
      data: [
        { value: dist.high || 0, itemStyle: { color: '#dc2626' } },
        { value: dist.medium || 0, itemStyle: { color: '#f59e0b' } },
        { value: dist.low || 0, itemStyle: { color: '#16a34a' } },
      ],
    }],
    grid: { left: 50, right: 20, top: 10, bottom: 30 },
  }
})

onMounted(fetchStats)
</script>
