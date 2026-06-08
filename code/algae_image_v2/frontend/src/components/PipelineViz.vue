<template>
  <div class="pipeline-viz">
    <el-row :gutter="16">
      <el-col :span="24">
        <h3 style="margin-bottom:16px; color:#1a3a5c;">
          <el-icon><Cpu /></el-icon> 偏振检测管线 — 中间结果可视化
        </h3>
      </el-col>
    </el-row>
    <el-row :gutter="12">
      <el-col
        v-for="(step, idx) in steps"
        :key="idx"
        :xs="24"
        :sm="12"
        :md="4"
        :lg="4"
        style="margin-bottom:12px"
      >
        <StepCard
          :title="step.title"
          :image="step.image"
          :description="step.description"
        />
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import StepCard from './StepCard.vue'

defineProps({
  steps: { type: Array, required: true },
})
</script>
