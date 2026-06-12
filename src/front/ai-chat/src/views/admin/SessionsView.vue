<script setup>
/**
 * SessionsView — 会话管理。
 *
 * 会话列表、详情查看、归档、删除。
 */
import { onMounted, ref } from 'vue'
import PageHeader from '@/components/common/PageHeader.vue'
import * as sessionApi from '@/api/sessions'

const sessions = ref([])
const loading = ref(false)
const detailVisible = ref(false)
const currentSession = ref(null)
const filterStatus = ref('')

onMounted(fetchSessions)

async function fetchSessions() {
  loading.value = true
  try {
    const params = { limit: 100 }
    if (filterStatus.value) params.status = filterStatus.value
    const { data } = await sessionApi.listSessions(params)
    sessions.value = data
  } finally {
    loading.value = false
  }
}

async function showDetail(id) {
  try {
    const { data } = await sessionApi.getSession(id)
    currentSession.value = data
    detailVisible.value = true
  } catch { /* 拦截器处理 */ }
}

async function archiveSession(id) {
  await sessionApi.archiveSession(id)
  await fetchSessions()
}

async function deleteSession(id) {
  await sessionApi.deleteSession(id)
  await fetchSessions()
}
</script>

<template>
  <div>
    <PageHeader title="会话管理" subtitle="查看、归档和管理对话会话" />

    <el-card shadow="hover">
      <template #header>
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <span class="font-medium">会话列表</span>
            <el-select v-model="filterStatus" placeholder="状态" clearable size="small" style="width: 120px" @change="fetchSessions">
              <el-option label="活跃" value="active" />
              <el-option label="已归档" value="archived" />
            </el-select>
          </div>
          <el-button size="small" @click="fetchSessions">刷新</el-button>
        </div>
      </template>
      <el-table :data="sessions" v-loading="loading" stripe>
        <el-table-column prop="session_id" label="ID" width="280" show-overflow-tooltip />
        <el-table-column prop="title" label="标题" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="message_count" label="消息数" width="100" />
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button text size="small" @click="showDetail(row.session_id)">详情</el-button>
            <el-button v-if="row.status === 'active'" text size="small" type="warning" @click="archiveSession(row.session_id)">归档</el-button>
            <el-popconfirm title="确认删除?" @confirm="deleteSession(row.session_id)">
              <template #reference>
                <el-button text size="small" type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailVisible" title="会话详情" width="650">
      <template v-if="currentSession">
        <el-descriptions :column="2" border class="mb-4">
          <el-descriptions-item label="ID">{{ currentSession.session_id }}</el-descriptions-item>
          <el-descriptions-item label="标题">{{ currentSession.title }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ currentSession.status }}</el-descriptions-item>
          <el-descriptions-item label="消息数">{{ currentSession.message_count }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ currentSession.created_at }}</el-descriptions-item>
          <el-descriptions-item label="最后活跃">{{ currentSession.last_active_at }}</el-descriptions-item>
        </el-descriptions>
        <div v-if="currentSession.messages?.length">
          <div class="text-sm font-medium mb-2">消息记录</div>
          <div class="max-h-80 overflow-y-auto">
            <div v-for="(msg, idx) in currentSession.messages" :key="idx" class="mb-3 p-3 bg-gray-50 rounded">
              <div class="text-xs text-gray-500 mb-1">{{ msg.role }}</div>
              <div class="text-sm text-gray-700 whitespace-pre-wrap">{{ msg.content }}</div>
            </div>
          </div>
        </div>
      </template>
    </el-dialog>
  </div>
</template>
