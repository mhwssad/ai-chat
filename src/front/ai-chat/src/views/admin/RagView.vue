<script setup>
/**
 * RagView — RAG 管理。
 *
 * 文档索引、搜索测试、文档管理、统计。
 */
import { onMounted, ref } from 'vue'
import PageHeader from '@/components/common/PageHeader.vue'
import * as ragApi from '@/api/rag'

const documents = ref([])
const stats = ref(null)
const loading = ref(false)

// 索引表单
const indexDialogVisible = ref(false)
const indexType = ref('file')
const indexForm = ref({})

// 搜索测试
const searchQuery = ref('')
const searchResults = ref([])
const searchMode = ref('vector')

onMounted(() => {
  fetchDocuments()
  fetchStats()
})

async function fetchDocuments() {
  loading.value = true
  try {
    const { data } = await ragApi.listDocuments()
    documents.value = data
  } finally {
    loading.value = false
  }
}

async function fetchStats() {
  try {
    const { data } = await ragApi.getStats()
    stats.value = data
  } catch { /* 拦截器处理 */ }
}

function openIndexDialog(type) {
  indexType.value = type
  indexForm.value = {}
  indexDialogVisible.value = true
}

async function submitIndex() {
  const form = indexForm.value
  switch (indexType.value) {
    case 'file': await ragApi.indexFile(form); break
    case 'url': await ragApi.indexUrl(form); break
    case 'text': await ragApi.indexText(form); break
    case 'directory': await ragApi.indexDirectory(form); break
  }
  indexDialogVisible.value = false
  await fetchDocuments()
  await fetchStats()
}

async function deleteDoc(path) {
  await ragApi.deleteDocument(path)
  await fetchDocuments()
  await fetchStats()
}

async function deleteAll() {
  await ragApi.deleteAllDocuments()
  await fetchDocuments()
  await fetchStats()
}

async function doSearch() {
  if (!searchQuery.value.trim()) return
  try {
    const api = searchMode.value === 'hybrid' ? ragApi.searchHybrid : ragApi.search
    const { data } = await api({ query: searchQuery.value })
    searchResults.value = data.results || data
  } catch { /* 拦截器处理 */ }
}
</script>

<template>
  <div>
    <PageHeader title="RAG 管理" subtitle="文档索引、向量搜索和知识库管理" />

    <!-- 统计 + 操作 -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
      <el-card shadow="hover">
        <template #header><span class="text-sm text-gray-500">文档数</span></template>
        <div class="text-2xl font-bold text-blue-600">{{ stats?.total_documents ?? 0 }}</div>
      </el-card>
      <el-card shadow="hover">
        <template #header><span class="text-sm text-gray-500">向量数</span></template>
        <div class="text-2xl font-bold text-green-600">{{ stats?.total_vectors ?? 0 }}</div>
      </el-card>
      <el-card shadow="hover" class="flex items-center justify-center">
        <el-button type="primary" @click="openIndexDialog('file')">索引文件</el-button>
        <el-button @click="openIndexDialog('url')">索引 URL</el-button>
        <el-button @click="openIndexDialog('text')">索引文本</el-button>
      </el-card>
      <el-card shadow="hover" class="flex items-center justify-center">
        <el-button @click="openIndexDialog('directory')">索引目录</el-button>
        <el-popconfirm title="确认删除全部文档?" @confirm="deleteAll">
          <template #reference>
            <el-button type="danger">清空文档</el-button>
          </template>
        </el-popconfirm>
      </el-card>
    </div>

    <!-- 搜索测试 -->
    <el-card shadow="hover" class="mb-6">
      <template #header><span class="font-medium">搜索测试</span></template>
      <div class="flex items-center gap-3 mb-4">
        <el-select v-model="searchMode" size="small" style="width: 120px">
          <el-option label="向量搜索" value="vector" />
          <el-option label="混合搜索" value="hybrid" />
        </el-select>
        <el-input v-model="searchQuery" placeholder="输入搜索内容..." @keyup.enter="doSearch" class="flex-1" />
        <el-button type="primary" @click="doSearch">搜索</el-button>
      </div>
      <div v-if="searchResults.length">
        <div v-for="(r, idx) in searchResults" :key="idx" class="border-b border-gray-100 py-3 last:border-0">
          <div class="text-sm text-gray-600">{{ r.content || r.text }}</div>
          <div v-if="r.score" class="text-xs text-gray-400 mt-1">相似度: {{ r.score?.toFixed(4) }}</div>
        </div>
      </div>
    </el-card>

    <!-- 文档列表 -->
    <el-card shadow="hover">
      <template #header><span class="font-medium">文档列表</span></template>
      <el-table :data="documents" v-loading="loading" stripe>
        <el-table-column prop="path" label="路径" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'indexed' ? 'success' : 'warning'" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="chunks" label="分块数" width="100" />
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-popconfirm title="确认删除?" @confirm="deleteDoc(row.path)">
              <template #reference>
                <el-button text size="small" type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 索引对话框 -->
    <el-dialog v-model="indexDialogVisible" :title="'索引' + indexType" width="500">
      <el-form label-width="80px">
        <el-form-item v-if="indexType === 'file'" label="文件路径">
          <el-input v-model="indexForm.file_path" placeholder="/path/to/file" />
        </el-form-item>
        <el-form-item v-if="indexType === 'url'" label="URL">
          <el-input v-model="indexForm.url" placeholder="https://..." />
        </el-form-item>
        <el-form-item v-if="indexType === 'text'" label="文本">
          <el-input v-model="indexForm.text" type="textarea" :rows="6" />
        </el-form-item>
        <el-form-item v-if="indexType === 'directory'" label="目录路径">
          <el-input v-model="indexForm.directory" placeholder="/path/to/dir" />
        </el-form-item>
        <el-form-item label="会话ID">
          <el-input v-model="indexForm.session_id" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="indexDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitIndex">开始索引</el-button>
      </template>
    </el-dialog>
  </div>
</template>
