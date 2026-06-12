<script setup>
/**
 * AgentView — Agent 配置面板。
 *
 * 运行 Agent、查看状态、取消/恢复、团队模式。
 */
import { ref } from 'vue'
import PageHeader from '@/components/common/PageHeader.vue'
import * as agentApi from '@/api/agent'

const runDialogVisible = ref(false)
const teamDialogVisible = ref(false)
const isRunning = ref(false)
const result = ref('')

// 运行表单
const runForm = ref({
  message: '',
  session_id: '',
  max_iterations: 5,
  use_tools: true,
})

// 团队表单
const teamMode = ref('orchestrator')
const teamForm = ref({
  message: '',
  agents: [],
})

async function runAgent() {
  isRunning.value = true
  result.value = ''
  try {
    const { data } = await agentApi.runAgent(runForm.value)
    result.value = JSON.stringify(data, null, 2)
  } catch {
    result.value = '运行失败'
  } finally {
    isRunning.value = false
  }
}

async function cancelAgent() {
  try {
    await agentApi.cancelAgent({})
    result.value += '\n已取消'
  } catch { /* 拦截器处理 */ }
}

async function runTeam() {
  isRunning.value = true
  result.value = ''
  try {
    const api = teamMode.value === 'orchestrator' ? agentApi.teamOrchestrator : agentApi.teamDebate
    const { data } = await api(teamForm.value)
    result.value = JSON.stringify(data, null, 2)
  } catch {
    result.value = '运行失败'
  } finally {
    isRunning.value = false
  }
}
</script>

<template>
  <div>
    <PageHeader title="Agent 配置" subtitle="运行和管理 AI Agent" />

    <!-- 操作按钮 -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
      <el-card shadow="hover" class="text-center">
        <h3 class="text-sm font-medium mb-3">单 Agent 运行</h3>
        <el-button type="primary" @click="runDialogVisible = true">启动 Agent</el-button>
        <el-button type="danger" class="ml-2" :disabled="!isRunning" @click="cancelAgent">取消运行</el-button>
      </el-card>
      <el-card shadow="hover" class="text-center">
        <h3 class="text-sm font-medium mb-3">团队模式</h3>
        <el-button type="primary" @click="teamDialogVisible = true">启动团队</el-button>
      </el-card>
    </div>

    <!-- 运行结果 -->
    <el-card v-if="result" shadow="hover" class="mb-6">
      <template #header>
        <div class="flex items-center justify-between">
          <span class="font-medium">运行结果</span>
          <el-tag v-if="isRunning" type="warning" size="small">运行中...</el-tag>
        </div>
      </template>
      <pre class="text-xs bg-gray-50 p-4 rounded overflow-auto max-h-96 whitespace-pre-wrap">{{ result }}</pre>
    </el-card>

    <!-- 单 Agent 对话框 -->
    <el-dialog v-model="runDialogVisible" title="启动 Agent" width="500">
      <el-form label-width="100px">
        <el-form-item label="消息"><el-input v-model="runForm.message" type="textarea" :rows="4" /></el-form-item>
        <el-form-item label="会话ID"><el-input v-model="runForm.session_id" placeholder="可选" /></el-form-item>
        <el-form-item label="最大迭代"><el-input-number v-model="runForm.max_iterations" :min="1" :max="50" /></el-form-item>
        <el-form-item label="使用工具"><el-switch v-model="runForm.use_tools" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="runDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="runDialogVisible = false; runAgent()">运行</el-button>
      </template>
    </el-dialog>

    <!-- 团队对话框 -->
    <el-dialog v-model="teamDialogVisible" title="启动团队" width="500">
      <el-form label-width="100px">
        <el-form-item label="模式">
          <el-radio-group v-model="teamMode">
            <el-radio value="orchestrator">编排者</el-radio>
            <el-radio value="debate">辩论</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="消息"><el-input v-model="teamForm.message" type="textarea" :rows="4" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="teamDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="teamDialogVisible = false; runTeam()">运行</el-button>
      </template>
    </el-dialog>
  </div>
</template>
