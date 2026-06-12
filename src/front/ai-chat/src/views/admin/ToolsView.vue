<script setup>
/**
 * ToolsView — 工具管理。
 *
 * 工具列表、详情、测试执行。
 */
import { onMounted, ref } from 'vue'
import PageHeader from '@/components/common/PageHeader.vue'
import * as toolsApi from '@/api/tools'

const tools = ref([])
const loading = ref(false)
const detailVisible = ref(false)
const executeVisible = ref(false)
const currentTool = ref(null)
const executeParams = ref('')
const executeResult = ref('')

onMounted(fetchTools)

async function fetchTools() {
  loading.value = true
  try {
    const { data } = await toolsApi.listTools()
    tools.value = data
  } finally {
    loading.value = false
  }
}

async function showDetail(name) {
  const { data } = await toolsApi.getTool(name)
  currentTool.value = data
  detailVisible.value = true
}

function openExecute(name) {
  currentTool.value = { name }
  executeParams.value = ''
  executeResult.value = ''
  executeVisible.value = true
}

async function runExecute() {
  try {
    const params = executeParams.value ? JSON.parse(executeParams.value) : {}
    const { data } = await toolsApi.executeTool(currentTool.value.name, params)
    executeResult.value = JSON.stringify(data, null, 2)
  } catch (e) {
    executeResult.value = `错误: ${e.message}`
  }
}
</script>

<template>
  <div>
    <PageHeader title="工具管理" subtitle="查看和测试已注册工具" />

    <el-card shadow="hover">
      <el-table :data="tools" v-loading="loading" stripe>
        <el-table-column prop="name" label="名称" width="200" />
        <el-table-column prop="description" label="描述" show-overflow-tooltip />
        <el-table-column prop="enabled" label="启用" width="80">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'info'" size="small">
              {{ row.enabled ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button text size="small" @click="showDetail(row.name)">详情</el-button>
            <el-button text size="small" type="primary" @click="openExecute(row.name)">测试</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailVisible" title="工具详情" width="600">
      <template v-if="currentTool">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="名称">{{ currentTool.name }}</el-descriptions-item>
          <el-descriptions-item label="描述">{{ currentTool.description }}</el-descriptions-item>
          <el-descriptions-item label="参数 Schema">
            <pre class="text-xs bg-gray-50 p-2 rounded overflow-auto max-h-60">{{ JSON.stringify(currentTool.parameters, null, 2) }}</pre>
          </el-descriptions-item>
        </el-descriptions>
      </template>
    </el-dialog>

    <!-- 测试执行对话框 -->
    <el-dialog v-model="executeVisible" title="测试执行" width="600">
      <div class="mb-4">
        <div class="text-sm text-gray-500 mb-2">参数 (JSON)</div>
        <el-input v-model="executeParams" type="textarea" :rows="4" placeholder='{"key": "value"}' />
      </div>
      <el-button type="primary" @click="runExecute" class="mb-4">执行</el-button>
      <div v-if="executeResult">
        <div class="text-sm text-gray-500 mb-2">结果</div>
        <pre class="text-xs bg-gray-50 p-3 rounded overflow-auto max-h-60">{{ executeResult }}</pre>
      </div>
    </el-dialog>
  </div>
</template>
