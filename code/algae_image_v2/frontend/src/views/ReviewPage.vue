<template>
  <div class="review-page" style="max-width:1000px; margin:0 auto">
    <!-- Stats -->
    <el-row :gutter="16" style="margin-bottom:16px">
      <el-col :xs="8">
        <el-card shadow="never">
          <div style="text-align:center">
            <div style="font-size:28px; font-weight:700; color:#16a34a">{{ stats.approved }}</div>
            <div style="font-size:12px; color:#999">已复核通过</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="8">
        <el-card shadow="never">
          <div style="text-align:center">
            <div style="font-size:28px; font-weight:700; color:#f59e0b">{{ stats.pending }}</div>
            <div style="font-size:12px; color:#999">待复核</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="8">
        <el-card shadow="never">
          <div style="text-align:center">
            <div style="font-size:28px; font-weight:700; color:#1976d2">{{ stats.total }}</div>
            <div style="font-size:12px; color:#999">总记录</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Actions -->
    <div style="display:flex; gap:10px; margin-bottom:16px">
      <el-button type="primary" :loading="batchLoading" @click="handleBatchPull">拉取低置信度样本</el-button>
      <el-radio-group v-model="filter" size="small" @change="fetchReviews">
        <el-radio-button value="">全部</el-radio-button>
        <el-radio-button value="pending">待复核</el-radio-button>
        <el-radio-button value="approved">已通过</el-radio-button>
        <el-radio-button value="rejected">已拒绝</el-radio-button>
      </el-radio-group>
    </div>

    <!-- Review List -->
    <el-card shadow="never">
      <template #header>
        <span style="font-weight:600; font-size:15px">复核记录</span>
        <p style="font-size:12px; color:#999; margin-top:2px">专家确认 · 标注修正 · 加入训练集</p>
      </template>

      <el-table :data="items" stripe v-loading="loading" empty-text="暂无复核记录">
        <el-table-column prop="filename" label="文件名" min-width="180" />
        <el-table-column prop="class_name_zh" label="藻种" width="120">
          <template #default="{ row }">
            {{ row.class_name_zh || row.class_name }}
          </template>
        </el-table-column>
        <el-table-column label="置信度" width="90">
          <template #default="{ row }">
            <span :style="{ color: row.confidence < 0.5 ? '#dc2626' : row.confidence < 0.7 ? '#f59e0b' : '#16a34a' }">
              {{ (row.confidence * 100).toFixed(0) }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column label="风险" width="70">
          <template #default="{ row }">
            <el-tag v-if="row.risk_level" :type="row.risk_level === 'high' ? 'danger' : row.risk_level === 'medium' ? 'warning' : 'success'" size="small">
              {{ { high: '高危', medium: '中危', low: '低危' }[row.risk_level] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'approved' ? 'success' : row.status === 'rejected' ? 'danger' : 'warning'" size="small">
              {{ { pending: '待复核', approved: '已通过', rejected: '已拒绝' }[row.status] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="时间" width="100">
          <template #default="{ row }">
            <span style="font-size:12px; color:#999">{{ row.created_at?.slice(0,16) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right" v-if="filter !== 'approved' && filter !== 'rejected'">
          <template #default="{ row }">
            <template v-if="row.status === 'pending'">
              <el-button type="success" size="small" @click="handleApprove(row)">通过</el-button>
              <el-button type="danger" size="small" @click="handleReject(row)">拒绝</el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { getReviews, submitReview, submitReviewBatch } from '@/api'
import { ElMessage } from 'element-plus'

const items = ref([])
const loading = ref(false)
const batchLoading = ref(false)
const filter = ref('pending')
const stats = reactive({ total: 0, approved: 0, pending: 0 })

async function fetchReviews() {
  loading.value = true
  try {
    const res = await getReviews(filter.value || null)
    const data = res.data
    items.value = data.items || []
    stats.total = data.total
    stats.approved = data.approved_count
    stats.pending = data.pending_count
  } catch (_) { /* backend may not be ready */ }
  finally { loading.value = false }
}

async function handleApprove(row) {
  try {
    await submitReview(row.detection_id, 'approved')
    ElMessage.success('已通过复核')
    await fetchReviews()
  } catch (_) { ElMessage.error('操作失败') }
}

async function handleReject(row) {
  try {
    await submitReview(row.detection_id, 'rejected')
    ElMessage.success('已拒绝')
    await fetchReviews()
  } catch (_) { ElMessage.error('操作失败') }
}

async function handleBatchPull() {
  batchLoading.value = true
  try {
    const res = await submitReviewBatch()
    ElMessage.success(`已拉取 ${res.data.added} 条低置信度样本`)
    await fetchReviews()
  } catch (_) { ElMessage.error('拉取失败') }
  finally { batchLoading.value = false }
}

onMounted(fetchReviews)
</script>
