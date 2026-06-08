<template>
  <el-card shadow="hover" class="step-card">
    <template #header>
      <div class="step-header">
        <el-tag type="primary" size="small">{{ title }}</el-tag>
      </div>
    </template>
    <el-image
      :src="image"
      fit="contain"
      style="width:100%; max-height:240px; background:#000"
    />
    <p class="step-desc">{{ description }}</p>
  </el-card>
</template>

<script setup>
defineProps({
  title: String,
  image: String,
  description: String,
})
</script>

<style scoped>
.step-card { text-align: center; }
.step-header { display: flex; justify-content: center; }
.step-desc { margin-top: 8px; font-size: 12px; color: #666; line-height: 1.5; }
</style>
