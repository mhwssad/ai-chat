<script setup>
/**
 * MemoryView — 记忆管理。
 *
 * 记忆列表、搜索、启用/禁用、统计。
 */
import { onMounted, ref } from 'vue'
import PageHeader from '@/components/common/PageHeader.vue'
import * as memoryApi from '@/api/memory'

const memories = ref([])
const stats = ref(null)
const loading = ref(false)
const searchQuery = ref('')
const searchResults = ref([])

// 过滤参数
const filterType = ref('')
const filterStatus = ref('')

onMounted(() => {
  fetchMemories()
  fetchStats()
})

async function fetchMemories() {
  loading.value = true
  try {
    const params = {}
    if (filterType.value) params.memory_type = filterType.value
    if (filterStatus.value) params.status = filterStatus.value
    const { data } = await memoryApi.listMemory(params)
    memories.value = data
  } finally {
    loading.value = false
  }
}

async function fetchStats() {
  try {
    const { data } = await memoryApi.getStats()
    stats.value = data
  } catch { /* 拦截器处理 */ }
}

async function searchMemories() {
  if (!searchQuery.value.trim()) return
  try {
    const { data } = await memoryApi.searchMemory({ query: searchQuery.value })
    searchResults.value = data
  } catch { /* 拦截器处理 */ }
}

async function toggleMemory(name, enabled) {
  if (enabled) {
    await memoryApi.enableMemory(name)
  } else {
    await memoryApi.disableMemory(name)
  }
  await fetchMemories()
}

async function deleteMemory(name) {
  await memoryApi.deleteMemory(name)
  await fetchMemories()
  await fetchStats()
}

async function rebuildIndex() {
  await memoryApi.rebuildIndex()
  await fetchStats()
}

function resetSearch() {
  searchQuery.value = ''
  searchResults.value = []
}
</script>

<template>
  <div>
    <PageHeader title="记忆管理" subtitle="查看、搜索和管理系统记忆" />

    <!-- 统计卡片 -->
    <div v-if="stats" class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      <el-card shadow="hover">
        <template #header><span class="text-sm text-gray-500">总记忆数</span></template>
        <div class="text-2xl font-bold text-blue-600">{{ stats.total ?? 0 }}</div>
      </el-card>
      <el-card shadow="hover">
        <template #header><span class="text-sm text-gray-500">已启用</span></template>
        <div class="text-2xl font-bold text-green-600">{{ stats.enabled ?? 0 }}</div>
      </el-card>
      <el-card shadow="hover">
        <template #header><span class="text-sm text-gray-500">已禁用</span></template>
        <div class="text-2xl font-bold text-red-500">{{ stats.disabled ?? 0 }}</div>
      </el-card>
    </div>

    <!-- 搜索栏 -->
    <el-card shadow="hover" class="mb-6">
      <div class="flex items-center gap-3">
        <el-input v-model="searchQuery" placeholder="搜索记忆..." @keyup.enter="searchMemories" class="flex-1" />
        <el-button type="primary" @click="searchMemories">搜索</el-button>
        <el-button @click="resetSearch">重置</el-button>
        <el-button type="warning" @click="rebuildIndex">重建索引</el-button>
      </div>
    </el-card>

    <!-- 搜索结果 -->
    <el-card v-if="searchResults.length" shadow="hover" class="mb-6">
      <template #header><span class="font-medium">搜索结果</span></template>
      <el-table :data="searchResults" stripe>
        <el-table-column prop="name" label="名称" width="200" />
        <el-table-column prop="memory_type" label="类型" width="120" />
        <el-table-column prop="content" label="内容" show-overflow-tooltip />
      </el-table>
    </el-card>

    <!-- 过滤 + 列表 -->
    <el-card shadow="hover">
      <template #header>
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <el-select v-model="filterType" placeholder="类型" clearable size="small" style="width: 120px" @change="fetchMemories">
              <el-option label="用户" value="user" />
              <el-option label="项目" value="project" />
              <el-option label="反馈" value="feedback" />
              <el-option label="参考" value="reference" />
            </el-select>
            <el-select v-model="filterStatus" placeholder="状态" clearable size="small" style="width: 120px" @change="fetchMemories">
              <el-option label="已启用" value="enabled" />
              <el-option label="已禁用" value="disabled" />
            </el-select>
          </div>
          <span class="font-medium">记忆列表</span>
        </div>
      </template>
      <el-table :data="memories" v-loading="loading" stripe>
        <el-table-column prop="name" label="名称" width="200" />
        <el-table-column prop="memory_type" label="类型" width="120" />
        <el-table-column prop="description" label="描述" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-switch
              :model-value="row.status === 'enabled'"
              @change="(val) => toggleMemory(row.name, val)"
              size="small"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-popconfirm title="确认删除?" @confirm="deleteMemory(row.name)">
              <template #reference>
                <el-button text size="small" type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>
