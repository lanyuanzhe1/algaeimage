<template>
  <el-container class="app-container">
    <el-header class="app-header">
      <div class="brand" @click="$router.push('/')">
        <span class="brand-mark">藻</span>
        <div>
          <h1>藻影知微 有害藻华早期预警平台</h1>
          <p class="subtitle">基于偏振成像与深度学习图像识别的智能监测系统</p>
        </div>
      </div>
    </el-header>
    <el-main>
      <div class="nav-bar">
        <el-menu
          :default-active="currentRoute"
          mode="horizontal"
          :ellipsis="false"
          @select="handleSelect"
          class="nav-menu"
        >
          <el-menu-item index="/">首页</el-menu-item>
          <el-menu-item index="/detect">手动检测</el-menu-item>
          <el-menu-item index="/detect/live">实时监测</el-menu-item>
          <el-menu-item index="/history">历史记录</el-menu-item>
          <el-menu-item index="/dashboard">数据统计</el-menu-item>
          <el-menu-item index="/devices">设备管理</el-menu-item>
          <el-menu-item index="/review">人工复核</el-menu-item>
        </el-menu>
      </div>
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const currentRoute = computed(() => route.path)

function handleSelect(index) {
  router.push(index)
}
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif; background: #f0f2f5; }
.app-header {
  background: linear-gradient(135deg, #1a3a5c 0%, #2d6a9f 100%);
  color: white;
  display: flex;
  align-items: center;
  height: 72px !important;
}
.brand {
  display: flex;
  align-items: center;
  gap: 16px;
  cursor: pointer;
}
.brand-mark {
  font-size: 32px;
  background: rgba(255,255,255,0.15);
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
}
.brand h1 { font-size: 20px; font-weight: 600; color: white; }
.subtitle { font-size: 12px; opacity: 0.75; margin-top: 2px; }
.nav-bar {
  display: flex;
  align-items: center;
  margin: -20px -20px 20px -20px;
  padding: 0 20px;
  background: white;
  border-bottom: 1px solid #e8e8e8;
}
.nav-menu {
  flex: 1;
  border-bottom: none !important;
}
.app-container { min-height: 100vh; }
</style>
