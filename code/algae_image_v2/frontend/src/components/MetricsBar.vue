<template>
  <el-row :gutter="16" style="margin-bottom:20px">
    <el-col v-for="card in cards" :key="card.label" :xs="12" :sm="8" :md="4">
      <el-card shadow="hover" class="metric-card">
        <span class="metric-label">{{ card.label }}</span>
        <strong :style="{ color: card.color || '#1a3a5c' }" class="metric-value">
          {{ card.value }}
        </strong>
        <small class="metric-sub">{{ card.sub }}</small>
      </el-card>
    </el-col>
  </el-row>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getStats } from '@/api'

const stats = ref(null)

async function fetchStats() {
  try {
    const res = await getStats()
    stats.value = res.data
  } catch (e) {
    // silently fail, cards show "--"
  }
}

const cards = computed(() => {
  if (!stats.value) {
    return [
      { label: '总检测次数', value: '--', sub: '累计检测样本' },
      { label: '今日检测', value: '--', sub: '当日处理量' },
      { label: '高危预警', value: '--', sub: '需立即关注', color: '#dc2626' },
      { label: '平均质量分', value: '--', sub: 'Q Score · 图像质量' },
      { label: '活跃藻种', value: '--', sub: '检出类别数' },
    ]
  }
  const s = stats.value
  const highCount = s.risk_distribution?.high || 0
  const avgQ = s.avg_q_score ? s.avg_q_score.toFixed(2) : '--'
  return [
    { label: '总检测次数', value: s.total_detections, sub: '累计检测样本' },
    { label: '今日检测', value: s.today_count, sub: '当日处理量' },
    { label: '高危预警', value: highCount, sub: '需立即关注', color: highCount ? '#dc2626' : '#16a34a' },
    { label: '平均质量分', value: avgQ, sub: 'Q Score · 图像质量', color: avgQ > 0.7 ? '#16a34a' : '#f59e0b' },
    { label: '活跃藻种', value: Object.keys(s.class_distribution || {}).length, sub: '检出类别数' },
  ]
})

onMounted(fetchStats)
</script>

<style scoped>
.metric-card { text-align: center; }
.metric-label { font-size: 13px; color: #999; display: block; }
.metric-value { font-size: 28px; font-weight: 700; display: block; margin: 4px 0; }
.metric-sub { font-size: 11px; color: #bbb; }
</style>
