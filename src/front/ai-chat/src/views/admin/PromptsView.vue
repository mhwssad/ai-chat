<script setup>
/**
 * PromptsView — 提示词模板管理。
 *
 * CRUD + 渲染测试 + 版本管理。
 */
import { onMounted, ref } from 'vue'
import PageHeader from '@/components/common/PageHeader.vue'
import * as promptsApi from '@/api/prompts'

const prompts = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const renderDialogVisible = ref(false)
const versionDialogVisible = ref(false)
const isEditing = ref(false)

const form = ref({ prompt_key: '', content: '', description: '', category: '' })
const renderForm = ref({ prompt_key: '', variables: {} })
const renderedResult = ref('')
const versions = ref([])

onMounted(fetchPrompts)

async function fetchPrompts() {
  loading.value = true
  try {
    const { data } = await promptsApi.listPrompts()
    prompts.value = data
  } finally {
    loading.value = false
  }
}

function openDialog(row) {
  if (row) {
    isEditing.value = true
    form.value = { ...row }
  } else {
    isEditing.value = false
    form.value = { prompt_key: '', content: '', description: '', category: '' }
  }
  dialogVisible.value = true
}

async function save() {
  if (isEditing.value) {
    await promptsApi.updatePrompt(form.value.prompt_key, form.value)
  } else {
    await promptsApi.createPrompt(form.value)
  }
  dialogVisible.value = false
  await fetchPrompts()
}

async function deletePrompt(key) {
  await promptsApi.deletePrompt(key)
  await fetchPrompts()
}

async function openRender(key) {
  renderForm.value = { prompt_key: key, variables: {} }
  renderedResult.value = ''
  renderDialogVisible.value = true
}

async function doRender() {
  try {
    const { data } = await promptsApi.renderPrompt(renderForm.value)
    renderedResult.value = data.rendered || data.content || JSON.stringify(data, null, 2)
  } catch { /* 拦截器处理 */ }
}

async function showVersions(key) {
  try {
    const { data } = await promptsApi.listVersions(key)
    versions.value = data
    versionDialogVisible.value = true
  } catch { /* 拦截器处理 */ }
}

async function rollback(key, version) {
  await promptsApi.rollback(key, { version })
  versionDialogVisible.value = false
  await fetchPrompts()
}
</script>

<template>
  <div>
    <PageHeader title="提示词模板" subtitle="管理提示词模板和版本" />

    <el-card shadow="hover">
      <template #header>
        <div class="flex items-center justify-between">
          <span class="font-medium">提示词列表</span>
          <el-button type="primary" size="small" @click="openDialog()">新增模板</el-button>
        </div>
      </template>
      <el-table :data="prompts" v-loading="loading" stripe>
        <el-table-column prop="prompt_key" label="Key" width="180" />
        <el-table-column prop="category" label="分类" width="120" />
        <el-table-column prop="description" label="描述" show-overflow-tooltip />
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button text size="small" @click="openDialog(row)">编辑</el-button>
            <el-button text size="small" type="primary" @click="openRender(row.prompt_key)">渲染</el-button>
            <el-button text size="small" @click="showVersions(row.prompt_key)">版本</el-button>
            <el-popconfirm title="确认删除?" @confirm="deletePrompt(row.prompt_key)">
              <template #reference>
                <el-button text size="small" type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEditing ? '编辑模板' : '新增模板'" width="650">
      <el-form :model="form" label-width="80px">
        <el-form-item label="Key"><el-input v-model="form.prompt_key" :disabled="isEditing" /></el-form-item>
        <el-form-item label="分类"><el-input v-model="form.category" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" /></el-form-item>
        <el-form-item label="内容"><el-input v-model="form.content" type="textarea" :rows="8" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <!-- 渲染测试对话框 -->
    <el-dialog v-model="renderDialogVisible" title="渲染测试" width="600">
      <div class="mb-4">
        <div class="text-sm text-gray-500 mb-2">模板: {{ renderForm.prompt_key }}</div>
        <el-input v-model="renderForm.variables" type="textarea" :rows="4" placeholder='{"var": "value"}' />
      </div>
      <el-button type="primary" @click="doRender" class="mb-4">渲染</el-button>
      <div v-if="renderedResult">
        <pre class="text-xs bg-gray-50 p-3 rounded overflow-auto max-h-60 whitespace-pre-wrap">{{ renderedResult }}</pre>
      </div>
    </el-dialog>

    <!-- 版本历史对话框 -->
    <el-dialog v-model="versionDialogVisible" title="版本历史" width="600">
      <el-table :data="versions" stripe max-height="400">
        <el-table-column prop="version" label="版本" width="80" />
        <el-table-column prop="updated_at" label="时间" width="180" />
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button text size="small" @click="rollback(versions[0]?.prompt_key, row.version)">回滚</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>
