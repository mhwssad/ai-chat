<script setup>
/**
 * ModelsView — 模型配置管理。
 *
 * 供应商 + 模型 CRUD，测试连通性。
 */
import { onMounted, ref } from 'vue'
import PageHeader from '@/components/common/PageHeader.vue'
import * as modelsApi from '@/api/models'

const providers = ref([])
const models = ref([])
const loading = ref(false)
const providerDialogVisible = ref(false)
const modelDialogVisible = ref(false)
const isEditingProvider = ref(false)
const isEditingModel = ref(false)

const providerForm = ref({ provider_key: '', name: '', base_url: '', api_key: '', provider_type: '' })
const modelForm = ref({ model_key: '', name: '', model_type: '', provider_key: '', capability: '', enabled: true })

onMounted(() => {
  fetchProviders()
  fetchModels()
})

async function fetchProviders() {
  loading.value = true
  try {
    const { data } = await modelsApi.listProviders()
    providers.value = data
  } finally {
    loading.value = false
  }
}

async function fetchModels() {
  try {
    const { data } = await modelsApi.listModels()
    models.value = data
  } catch { /* 拦截器处理 */ }
}

function openProviderDialog(row) {
  if (row) {
    isEditingProvider.value = true
    providerForm.value = { ...row }
  } else {
    isEditingProvider.value = false
    providerForm.value = { provider_key: '', name: '', base_url: '', api_key: '', provider_type: '' }
  }
  providerDialogVisible.value = true
}

async function saveProvider() {
  if (isEditingProvider.value) {
    await modelsApi.updateProvider(providerForm.value.provider_key, providerForm.value)
  } else {
    await modelsApi.createProvider(providerForm.value)
  }
  providerDialogVisible.value = false
  await fetchProviders()
}

async function deleteProvider(key) {
  await modelsApi.deleteProvider(key)
  await fetchProviders()
}

function openModelDialog(row) {
  if (row) {
    isEditingModel.value = true
    modelForm.value = { ...row }
  } else {
    isEditingModel.value = false
    modelForm.value = { model_key: '', name: '', model_type: '', provider_key: '', capability: '', enabled: true }
  }
  modelDialogVisible.value = true
}

async function saveModel() {
  if (isEditingModel.value) {
    await modelsApi.updateModel(modelForm.value.model_key, modelForm.value)
  } else {
    await modelsApi.createModel(modelForm.value)
  }
  modelDialogVisible.value = false
  await fetchModels()
}

async function deleteModel(key) {
  await modelsApi.deleteModel(key)
  await fetchModels()
}

async function testModel(key) {
  await modelsApi.testModel(key)
}
</script>

<template>
  <div>
    <PageHeader title="模型配置" subtitle="管理供应商和模型" />

    <!-- 供应商 -->
    <el-card shadow="hover" class="mb-6">
      <template #header>
        <div class="flex items-center justify-between">
          <span class="font-medium">供应商</span>
          <el-button type="primary" size="small" @click="openProviderDialog()">新增供应商</el-button>
        </div>
      </template>
      <el-table :data="providers" v-loading="loading" stripe>
        <el-table-column prop="provider_key" label="Key" width="140" />
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="provider_type" label="类型" width="140" />
        <el-table-column prop="base_url" label="Base URL" show-overflow-tooltip />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button text size="small" @click="openProviderDialog(row)">编辑</el-button>
            <el-popconfirm title="确认删除?" @confirm="deleteProvider(row.provider_key)">
              <template #reference>
                <el-button text size="small" type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 模型 -->
    <el-card shadow="hover">
      <template #header>
        <div class="flex items-center justify-between">
          <span class="font-medium">模型</span>
          <el-button type="primary" size="small" @click="openModelDialog()">新增模型</el-button>
        </div>
      </template>
      <el-table :data="models" stripe>
        <el-table-column prop="model_key" label="Key" width="140" />
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="model_type" label="类型" width="120" />
        <el-table-column prop="provider_key" label="供应商" width="140" />
        <el-table-column prop="capability" label="能力" width="120" />
        <el-table-column prop="enabled" label="启用" width="80">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'info'" size="small">
              {{ row.enabled ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button text size="small" @click="testModel(row.model_key)">测试</el-button>
            <el-button text size="small" @click="openModelDialog(row)">编辑</el-button>
            <el-popconfirm title="确认删除?" @confirm="deleteModel(row.model_key)">
              <template #reference>
                <el-button text size="small" type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 供应商对话框 -->
    <el-dialog v-model="providerDialogVisible" :title="isEditingProvider ? '编辑供应商' : '新增供应商'" width="500">
      <el-form :model="providerForm" label-width="100px">
        <el-form-item label="Key"><el-input v-model="providerForm.provider_key" :disabled="isEditingProvider" /></el-form-item>
        <el-form-item label="名称"><el-input v-model="providerForm.name" /></el-form-item>
        <el-form-item label="类型"><el-input v-model="providerForm.provider_type" /></el-form-item>
        <el-form-item label="Base URL"><el-input v-model="providerForm.base_url" /></el-form-item>
        <el-form-item label="API Key"><el-input v-model="providerForm.api_key" type="password" show-password /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="providerDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveProvider">保存</el-button>
      </template>
    </el-dialog>

    <!-- 模型对话框 -->
    <el-dialog v-model="modelDialogVisible" :title="isEditingModel ? '编辑模型' : '新增模型'" width="500">
      <el-form :model="modelForm" label-width="100px">
        <el-form-item label="Key"><el-input v-model="modelForm.model_key" :disabled="isEditingModel" /></el-form-item>
        <el-form-item label="名称"><el-input v-model="modelForm.name" /></el-form-item>
        <el-form-item label="类型"><el-input v-model="modelForm.model_type" /></el-form-item>
        <el-form-item label="供应商"><el-input v-model="modelForm.provider_key" /></el-form-item>
        <el-form-item label="能力"><el-input v-model="modelForm.capability" /></el-form-item>
        <el-form-item label="启用"><el-switch v-model="modelForm.enabled" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="modelDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveModel">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
