<template>
  <div class="review-page" style="max-width:800px; margin:0 auto">
    <el-card shadow="never">
      <template #header>
        <span style="font-weight:600; font-size:16px">人工复核</span>
        <p style="font-size:12px; color:#999; margin-top:2px">专家确认 · 标注修正 · 加入训练集</p>
      </template>

      <el-empty description="人工复核模块将在后续版本开放">
        <template #image>
          <el-icon :size="64" color="#ccc"><CircleCheckFilled /></el-icon>
        </template>
      </el-empty>

      <p style="text-align:center; color:#999; font-size:13px; max-width:500px; margin:0 auto 24px">
        届时支持：低置信度样本专家确认 · 误检/漏检标注修正 · 样本加入增量训练池 · 复核历史追踪
      </p>

      <DataLoop />
    </el-card>
  </div>
</template>

<script setup>
import DataLoop from '@/components/DataLoop.vue'
</script>
