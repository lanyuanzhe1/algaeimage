<template>
  <div class="home">
    <el-row :gutter="24" style="margin-bottom:24px">
      <el-col :span="24">
        <el-card shadow="never" class="hero-card">
          <h2 style="color:#1a3a5c; font-size:24px; margin-bottom:12px">
            基于偏振成像与深度学习的藻类智能检测系统
          </h2>
          <p style="color:#666; font-size:15px; line-height:1.8; max-width:800px">
            本系统融合 DoFP 偏振相机、HSV 色彩空间偏振模拟、
            I_enh v2 去散射增强算法与 YOLOv8 深度学习模型，
            实现水体藻类的快速、全自动化分类检测与风险预警。
          </p>
        </el-card>
      </el-col>
    </el-row>

    <!-- Pipeline steps -->
    <el-row :gutter="16" style="margin-bottom:24px">
      <el-col :span="24">
        <h3 style="margin-bottom:16px; color:#1a3a5c">检测管线</h3>
      </el-col>
    </el-row>
    <el-steps :active="5" align-center finish-status="success">
      <el-step title="偏振采集" description="DoFP相机多角度" />
      <el-step title="偏振模拟" description="HSV色彩空间法" />
      <el-step title="图像增强" description="I_enh v2去散射" />
      <el-step title="YOLO识别" description="深度学习分类框选" />
      <el-step title="融合预警" description="风险分级四级预警" />
    </el-steps>

    <!-- Feature cards -->
    <el-row :gutter="20" style="margin-top:36px">
      <el-col :xs="24" :sm="8" v-for="feat in features" :key="feat.title">
        <el-card shadow="hover" class="feature-card">
          <div class="feature-icon">
            <el-icon :size="32"><component :is="feat.icon" /></el-icon>
          </div>
          <h4>{{ feat.title }}</h4>
          <p>{{ feat.desc }}</p>
        </el-card>
      </el-col>
    </el-row>

    <!-- Quick start button -->
    <div style="text-align:center; margin-top:36px">
      <el-button type="primary" size="large" @click="$router.push('/detect')">
        开始检测 <el-icon><ArrowRight /></el-icon>
      </el-button>
    </div>
  </div>
</template>

<script setup>
const features = [
  {
    icon: 'Camera',
    title: '偏振成像',
    desc: '基于 DoFP 分焦平面偏振相机，单次曝光获取多角度偏振信息，突破传统明场显微限制。',
  },
  {
    icon: 'Cpu',
    title: '智能识别',
    desc: 'YOLOv8 深度学习模型，5 类 FMPD 藻种高精度检测，置信度与风险等级实时输出。',
  },
  {
    icon: 'Warning',
    title: '风险预警',
    desc: '基于藻种产毒特性与密度阈值，四级预警机制，辅助水质安全管理决策。',
  },
]
</script>

<style scoped>
.home { max-width: 1000px; margin: 0 auto; }
.hero-card { border-left: 4px solid #1a3a5c; }
.feature-card { text-align: center; padding: 8px 0; }
.feature-icon { color: #2d6a9f; margin-bottom: 12px; }
.feature-card h4 { font-size: 16px; margin-bottom: 8px; color: #1a3a5c; }
.feature-card p { font-size: 13px; color: #888; line-height: 1.6; }
</style>
