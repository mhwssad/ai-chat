<script setup>
/**
 * SchedulerView — 定时任务管理。
 *
 * 任务 CRUD、启停控制、执行日志、统计。
 */
import { onMounted, ref } from 'vue'
import PageHeader from '@/components/common/PageHeader.vue'
import * as schedulerApi from '@/api/scheduler'

const tasks = ref([])
const stats = ref(null)
const loading = ref(false)
const createDialogVisible = ref(false)
const logsDialogVisible = ref(false)
const taskLogs = ref([])
const currentTaskId = ref(null)

// 创建表单
const taskType = ref('cron')
const taskForm = ref({ name: '', prompt: '', cron: '', interval: 0 })

const filterStatus = ref('')

onMounted(() => {
  fetchTasks()
  fetchStats()
})

async function fetchTasks() {
  loading.value = true
  try {
    const params = {}
    if (filterStatus.value) params.status = filterStatus.value
    const { data } = await schedulerApi.listTasks(params)
    tasks.value = data
  } finally {
    loading.value = false
  }
}

async function fetchStats() {
  try {
    const { data } = await schedulerApi.getStats()
    stats.value = data
  } catch { /* 拦截器处理 */ }
}

async function createTask() {
  const form = taskForm.value
  switch (taskType.value) {
    case 'cron': await schedulerApi.createCron(form); break
    case 'interval': await schedulerApi.createInterval(form); break
    case 'one-shot': await schedulerApi.createOneShot(form); break
  }
  createDialogVisible.value = false
  await fetchTasks()
  await fetchStats()
}

async function toggleTask(id, action) {
  await schedulerApi[`${action}Task`](id)
  await fetchTasks()
  await fetchStats()
}

async function deleteTask(id) {
  await schedulerApi.deleteTask(id)
  await fetchTasks()
  await fetchStats()
}

async function showLogs(id) {
  currentTaskId.value = id
  try {
    const { data } = await schedulerApi.getTaskLogs(id, { limit: 50 })
    taskLogs.value = data
  } catch { /* 拦截器处理 */ }
  logsDialogVisible.value = true
}

function statusTag(status) {
  const map = { running: 'success', paused: 'warning', stopped: 'info', error: 'danger' }
  return map[status] || 'info'
}
</script>

<template>
  <div>
    <PageHeader title="定时任务" subtitle="管理和监控定时调度任务" />

    <!-- 统计 -->
    <div v-if="stats" class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      <el-card shadow="hover">
        <template #header><span class="text-sm text-gray-500">总任务</span></template>
        <div class="text-2xl font-bold text-blue-600">{{ stats.total ?? 0 }}</div>
      </el-card>
      <el-card shadow="hover">
        <template #header><span class="text-sm text-gray-500">运行中</span></template>
        <div class="text-2xl font-bold text-green-600">{{ stats.running ?? 0 }}</div>
      </el-card>
      <el-card shadow="hover">
        <template #header><span class="text-sm text-gray-500">已暂停</span></template>
        <div class="text-2xl font-bold text-orange-600">{{ stats.paused ?? 0 }}</div>
      </el-card>
    </div>

    <!-- 任务列表 -->
    <el-card shadow="hover">
      <template #header>
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <span class="font-medium">任务列表</span>
            <el-select v-model="filterStatus" placeholder="状态" clearable size="small" style="width: 120px" @change="fetchTasks">
              <el-option label="运行中" value="running" />
              <el-option label="已暂停" value="paused" />
              <el-option label="已停止" value="stopped" />
            </el-select>
          </div>
          <el-button type="primary" size="small" @click="createDialogVisible = true; taskType = 'cron'">创建任务</el-button>
        </div>
      </template>
      <el-table :data="tasks" v-loading="loading" stripe>
        <el-table-column prop="name" label="名称" width="180" />
        <el-table-column prop="task_type" label="类型" width="120" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="prompt" label="提示词" show-overflow-tooltip />
        <el-table-column prop="last_run" label="上次运行" width="180" />
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <template v-if="row.status === 'running'">
              <el-button text size="small" type="warning" @click="toggleTask(row.id, 'pause')">暂停</el-button>
            </template>
            <template v-if="row.status === 'paused'">
              <el-button text size="small" type="success" @click="toggleTask(row.id, 'resume')">恢复</el-button>
            </template>
            <template v-if="row.status === 'stopped'">
              <el-button text size="small" type="success" @click="toggleTask(row.id, 'enable')">启用</el-button>
            </template>
            <el-button text size="small" @click="showLogs(row.id)">日志</el-button>
            <el-popconfirm title="确认删除?" @confirm="deleteTask(row.id)">
              <template #reference>
                <el-button text size="small" type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 创建对话框 -->
    <el-dialog v-model="createDialogVisible" title="创建定时任务" width="500">
      <el-form label-width="80px">
        <el-form-item label="任务类型">
          <el-radio-group v-model="taskType">
            <el-radio value="cron">Cron</el-radio>
            <el-radio value="interval">Interval</el-radio>
            <el-radio value="one-shot">一次性</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="名称"><el-input v-model="taskForm.name" /></el-form-item>
        <el-form-item v-if="taskType === 'cron'" label="Cron">
          <el-input v-model="taskForm.cron" placeholder="*/5 * * * *" />
        </el-form-item>
        <el-form-item v-if="taskType === 'interval'" label="间隔(秒)">
          <el-input-number v-model="taskForm.interval" :min="1" />
        </el-form-item>
        <el-form-item label="提示词"><el-input v-model="taskForm.prompt" type="textarea" :rows="4" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createTask">创建</el-button>
      </template>
    </el-dialog>

    <!-- 日志对话框 -->
    <el-dialog v-model="logsDialogVisible" title="执行日志" width="700">
      <el-table :data="taskLogs" stripe max-height="400">
        <el-table-column prop="run_at" label="时间" width="180" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="result" label="结果" show-overflow-tooltip />
      </el-table>
    </el-dialog>
  </div>
</template>
