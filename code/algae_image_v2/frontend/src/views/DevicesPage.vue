<template>
  <div class="devices-page" style="max-width:900px; margin:0 auto">
    <!-- Device List -->
    <el-card shadow="never" style="margin-bottom:16px">
      <template #header>
        <div style="display:flex; align-items:center; justify-content:space-between">
          <div>
            <span style="font-weight:600; font-size:16px">设备管理 · 多点位监测</span>
            <p style="font-size:12px; color:#999; margin-top:2px">在线设备 · 实时状态 · 远程运维</p>
          </div>
          <el-button type="primary" @click="showAddDialog = true">添加设备</el-button>
        </div>
      </template>

      <el-table :data="devices" stripe v-loading="loading" empty-text="暂无设备">
        <el-table-column prop="name" label="设备名称" min-width="180" />
        <el-table-column prop="location" label="位置" min-width="120" />
        <el-table-column prop="model" label="型号" width="150" />
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'online' ? 'success' : 'info'" size="small" effect="light">
              {{ row.status === 'online' ? '在线' : '离线' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="today_frames" label="今日帧数" width="90" />
        <el-table-column prop="alerts" label="预警" width="70">
          <template #default="{ row }">
            <span :style="{ color: row.alerts ? '#dc2626' : '#16a34a', fontWeight: 600 }">{{ row.alerts }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="uptime" label="运行时长" width="90" />
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-popconfirm title="确认删除此设备？" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button type="danger" size="small" text>删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <p v-if="!loading && !devices.length" style="text-align:center; color:#999; padding:20px">
        暂无设备 — 点击「添加设备」注册第一个监测点
      </p>
    </el-card>

    <!-- System Status -->
    <el-card shadow="never">
      <template #header>
        <span style="font-weight:600; font-size:15px">系统组件状态</span>
        <p style="font-size:12px; color:#999; margin-top:2px">相机 · 光源 · 网络 · 供电</p>
      </template>
      <div class="status-grid">
        <div class="status-item">
          <span>偏振相机模块</span>
          <el-progress :percentage="100" :stroke-width="10" color="#16a34a" />
        </div>
        <div class="status-item">
          <span>暗场光源</span>
          <el-progress :percentage="91" :stroke-width="10" color="#f59e0b" />
        </div>
        <div class="status-item">
          <span>网络链路</span>
          <el-progress :percentage="88" :stroke-width="10" color="#f59e0b" />
        </div>
        <div class="status-item">
          <span>供电系统</span>
          <el-progress :percentage="82" :stroke-width="10" color="#f59e0b" />
        </div>
        <div class="status-item">
          <span>窗口清洁度</span>
          <el-progress :percentage="72" :stroke-width="10" color="#ea580c" />
        </div>
      </div>
    </el-card>

    <!-- Add Device Dialog -->
    <el-dialog v-model="showAddDialog" title="添加设备" width="420px">
      <el-form label-width="80px">
        <el-form-item label="设备名称">
          <el-input v-model="newDevice.name" placeholder="如：主监测点 · 太湖A" />
        </el-form-item>
        <el-form-item label="位置">
          <el-input v-model="newDevice.location" placeholder="如：无锡 · 梅梁湾" />
        </el-form-item>
        <el-form-item label="型号">
          <el-input v-model="newDevice.model" placeholder="MV-CA013-20GC" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" :loading="adding" @click="handleAdd">确认添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getDevices, addDevice, deleteDevice } from '@/api'
import { ElMessage } from 'element-plus'

const devices = ref([])
const loading = ref(false)
const showAddDialog = ref(false)
const adding = ref(false)
const newDevice = ref({ name: '', location: '', model: 'MV-CA013-20GC' })

async function fetchDevices() {
  loading.value = true
  try {
    const res = await getDevices()
    devices.value = res.data.devices || []
  } catch (_) { /* backend may not be ready */ }
  finally { loading.value = false }
}

async function handleAdd() {
  if (!newDevice.value.name) { ElMessage.warning('请输入设备名称'); return }
  adding.value = true
  try {
    await addDevice(newDevice.value.name, newDevice.value.location, newDevice.value.model)
    ElMessage.success('设备已添加')
    showAddDialog.value = false
    newDevice.value = { name: '', location: '', model: 'MV-CA013-20GC' }
    await fetchDevices()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '添加失败')
  } finally { adding.value = false }
}

async function handleDelete(id) {
  try {
    await deleteDevice(id)
    ElMessage.success('设备已删除')
    await fetchDevices()
  } catch (_) { ElMessage.error('删除失败') }
}

onMounted(fetchDevices)
</script>

<style scoped>
.status-grid { display: grid; gap: 14px; }
.status-item { display: flex; align-items: center; gap: 16px; padding: 6px 0; }
.status-item span { width: 110px; font-size: 13px; color: #666; flex-shrink: 0; }
</style>
