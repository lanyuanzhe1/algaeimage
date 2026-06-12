<template>
  <el-card shadow="never" class="data-loop">
    <template #header>
      <span style="font-weight:600; font-size:15px">数据闭环</span>
      <p style="font-size:12px; color:#999; margin-top:2px">采集 → 识别 → 复核 → 再训练</p>
    </template>

    <div class="loop-flow">
      <div class="loop-node done">
        <span class="dot">✓</span>
        <label>采集</label>
        <small>偏振暗场成像</small>
      </div>
      <div class="loop-arrow">→</div>
      <div class="loop-node done">
        <span class="dot">✓</span>
        <label>识别</label>
        <small>YOLO分类计数</small>
      </div>
      <div class="loop-arrow">→</div>
      <div class="loop-node">
        <span class="dot">3</span>
        <label>复核</label>
        <small>等待专家确认</small>
      </div>
      <div class="loop-arrow">→</div>
      <div class="loop-node">
        <span class="dot">4</span>
        <label>再训练</label>
        <small>待加入样本池</small>
      </div>
    </div>

    <p class="loop-hint">人工复核与增量训练功能将在后续版本开放</p>
  </el-card>
</template>

<style scoped>
.loop-flow {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  flex-wrap: wrap;
}

.loop-node {
  text-align: center;
  padding: 8px 6px;
  min-width: 60px;
}

.loop-node.done .dot {
  background: #16a34a;
  color: white;
}

.dot {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  font-size: 12px;
  font-weight: 700;
  background: #e5e7eb;
  color: #6b7280;
  margin-bottom: 4px;
}

.loop-node label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: #333;
}

.loop-node small {
  display: block;
  font-size: 11px;
  color: #999;
  margin-top: 2px;
}

.loop-arrow {
  color: #ccc;
  font-size: 16px;
  margin-bottom: 20px;
}

.loop-hint {
  text-align: center;
  font-size: 12px;
  color: #bbb;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
}
</style>
