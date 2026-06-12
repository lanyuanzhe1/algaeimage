<template>
  <el-table :data="detections" stripe border style="width:100%; margin-top:20px" max-height="400">
    <el-table-column prop="class_name_zh" label="藻种" min-width="140" />
    <el-table-column prop="class_name" label="学名" min-width="160" />
    <el-table-column prop="confidence" label="置信度" width="100" sortable>
      <template #default="{ row }">
        <span :style="{ color: row.confidence > 0.7 ? '#16a34a' : row.confidence > 0.4 ? '#f59e0b' : '#dc2626' }">
          {{ (row.confidence * 100).toFixed(1) }}%
        </span>
      </template>
    </el-table-column>
    <el-table-column prop="risk_level" label="风险等级" width="100">
      <template #default="{ row }">
        <el-tag
          :type="row.risk_level === 'high' ? 'danger' : row.risk_level === 'medium' ? 'warning' : 'success'"
          size="small"
        >
          {{ riskLabel(row.risk_level) }}
        </el-tag>
      </template>
    </el-table-column>
  </el-table>
</template>

<script setup>
defineProps({
  detections: { type: Array, required: true },
})

function riskLabel(level) {
  return { high: '高危', medium: '中危', low: '低危' }[level] || level
}
</script>
