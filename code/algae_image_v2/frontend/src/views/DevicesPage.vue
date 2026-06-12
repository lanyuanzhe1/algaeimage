<template>
  <div class="devices-page" style="max-width:800px; margin:0 auto">
    <el-card shadow="never">
      <template #header>
        <span style="font-weight:600; font-size:16px">设备管理</span>
        <p style="font-size:12px; color:#999; margin-top:2px">偏振相机 · 暗场光源 · 运维状态</p>
      </template>

      <el-empty description="设备管理模块将在后续版本开放">
        <template #image>
          <el-icon :size="64" color="#ccc"><Setting /></el-icon>
        </template>
      </el-empty>

      <p style="text-align:center; color:#999; font-size:13px; max-width:500px; margin:0 auto 24px">
        届时支持：DoFP偏振相机状态监控 · 暗场光源校准 · 成像窗口清洁度检测 · 网络链路诊断
      </p>

      <div style="max-width:400px; margin:0 auto">
        <div class="device-row">
          <span>偏振相机</span>
          <el-progress :percentage="100" :stroke-width="10" color="#16a34a" />
        </div>
        <div class="device-row">
          <span>暗场光源</span>
          <el-progress :percentage="100" :stroke-width="10" color="#16a34a" />
        </div>
        <div class="device-row">
          <span>网络链路</span>
          <el-progress :percentage="100" :stroke-width="10" color="#16a34a" />
        </div>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.device-row {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 0;
}

.device-row span {
  width: 80px;
  font-size: 13px;
  color: #666;
  flex-shrink: 0;
}

.device-row .el-progress {
  flex: 1;
}
</style>
