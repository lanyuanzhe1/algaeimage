<template>
  <el-row :gutter="16">
    <el-col v-for="card in cards" :key="card.label" :xs="12" :sm="8" :md="4">
      <el-card shadow="hover" class="stat-card">
        <span class="stat-label">{{ card.label }}</span>
        <strong :style="{ color: card.color || '#1a3a5c' }" class="stat-value">
          {{ card.value }}
        </strong>
        <small class="stat-sub">{{ card.sub }}</small>
      </el-card>
    </el-col>
  </el-row>
</template>

<script setup>
defineProps({
  cards: { type: Array, required: true },
})
</script>

<style scoped>
.stat-card { text-align: center; }
.stat-label { font-size: 13px; color: #999; display: block; }
.stat-value { font-size: 28px; font-weight: 700; display: block; margin: 4px 0; }
.stat-sub { font-size: 11px; color: #bbb; }
</style>
