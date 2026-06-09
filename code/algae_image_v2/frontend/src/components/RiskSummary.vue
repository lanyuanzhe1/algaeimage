<template>
  <el-card shadow="never" class="risk-summary">
    <template #header>
      <span style="font-weight:600; font-size:15px">风险摘要</span>
      <p style="font-size:12px; color:#999; margin-top:2px">四级预警体系</p>
    </template>

    <div class="risk-badges">
      <span class="risk-badge badge-high">红色·高危</span>
      <span class="risk-badge badge-orange">橙色·预警</span>
      <span class="risk-badge badge-yellow">黄色·注意</span>
      <span class="risk-badge badge-low">绿色·低风险</span>
    </div>

    <ul class="risk-desc">
      <li><strong>红色</strong>：有害藻华爆发，需立即应急处置</li>
      <li><strong>橙色</strong>：藻密度快速上升，建议现场确认</li>
      <li><strong>黄色</strong>：指标抬升，增加采样频率</li>
      <li><strong>绿色</strong>：处于背景水平，正常监测</li>
    </ul>
  </el-card>
</template>

<style scoped>
.risk-badges {
  display: flex;
  gap: 6px;
  justify-content: center;
  flex-wrap: wrap;
  margin-bottom: 14px;
}

.risk-badge {
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 4px;
  font-weight: 600;
}

.badge-high {
  color: #dc2626;
  background: #fef2f2;
  border: 1px solid #fecaca;
}

.badge-orange {
  color: #d97706;
  background: #fffbeb;
  border: 1px solid #fde68a;
}

.badge-yellow {
  color: #ca8a04;
  background: #fefce8;
  border: 1px solid #fef08a;
}

.badge-low {
  color: #16a34a;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
}

.risk-desc {
  list-style: none;
  padding: 0;
  margin: 0;
  font-size: 13px;
  color: #666;
  line-height: 2;
}

.risk-desc strong {
  color: #333;
}
</style>
