<template>
  <div class="history-page" style="max-width:1000px; margin:0 auto">
    <el-card shadow="never">
      <template #header>
        <span style="font-size:16px; font-weight:600">检测历史记录</span>
      </template>

      <el-table :data="items" stripe v-loading="loading" empty-text="暂无检测记录">
        <el-table-column prop="filename" label="文件名" min-width="180" />
        <el-table-column prop="created_at" label="检测时间" width="180" />
        <el-table-column prop="q_score" label="质量评分" width="100">
          <template #default="{ row }">{{ row.q_score?.toFixed(2) || '--' }}</template>
        </el-table-column>
        <el-table-column prop="risk_level" label="风险等级" width="100">
          <template #default="{ row }">
            <el-tag
              v-if="row.risk_level"
              :type="row.risk_level === 'high' ? 'danger' : row.risk_level === 'medium' ? 'warning' : 'success'"
              size="small"
            >
              {{ { high: '高危', medium: '中危', low: '低危' }[row.risk_level] }}
            </el-tag>
            <span v-else style="color:#ccc">--</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="showDetail(row.id)">详情</el-button>
            <el-button size="small" type="danger" @click="removeItem(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-if="total > limit"
        style="margin-top:16px; justify-content:center"
        background
        layout="prev, pager, next"
        :total="total"
        :page-size="limit"
        v-model:current-page="page"
        @current-change="fetchHistory"
      />
    </el-card>

    <!-- Detail dialog -->
    <el-dialog v-model="dialogVisible" title="检测详情" width="700px">
      <div v-if="detail" style="max-height:500px; overflow-y:auto">
        <ResultTable v-if="detail.detections?.length" :detections="detail.detections" />
        <el-empty v-else description="该记录无检测结果" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getHistory, getHistoryDetail, deleteHistory } from '@/api'
import ResultTable from '@/components/ResultTable.vue'

const items = ref([])
const total = ref(0)
const page = ref(1)
const limit = 20
const loading = ref(false)
const dialogVisible = ref(false)
const detail = ref(null)

async function fetchHistory() {
  loading.value = true
  try {
    const res = await getHistory(page.value, limit)
    items.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

async function showDetail(id) {
  try {
    const res = await getHistoryDetail(id)
    detail.value = res.data
    dialogVisible.value = true
  } catch (e) { /* silently fail */ }
}

async function removeItem(id) {
  try {
    await deleteHistory(id)
    fetchHistory()
  } catch (e) { /* silently fail */ }
}

onMounted(fetchHistory)
</script>
