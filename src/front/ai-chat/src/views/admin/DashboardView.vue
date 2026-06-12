<script setup>
/**
 * DashboardView — 系统状态仪表盘。
 *
 * 展示系统运行状态和配置摘要。
 */
import { onMounted, ref } from 'vue'
import PageHeader from '@/components/common/PageHeader.vue'
import * as systemApi from '@/api/system'

const status = ref(null)
const config = ref(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const [statusRes, configRes] = await Promise.allSettled([
      systemApi.getStatus(),
      systemApi.getConfig(),
    ])
    if (statusRes.status === 'fulfilled') status.value = statusRes.value.data
    if (configRes.status === 'fulfilled') config.value = configRes.value.data
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div>
    <PageHeader title="仪表盘" subtitle="系统运行状态概览" />

    <el-skeleton :loading="loading" animated :rows="5">
      <!-- 状态卡片 -->
      <div v-if="status" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <el-card shadow="hover">
          <template #header><span class="text-sm text-gray-500">运行状态</span></template>
          <div class="text-2xl font-bold" :class="status.status === 'running' ? 'text-green-600' : 'text-red-500'">
            {{ status.status === 'running' ? '运行中' : '已停止' }}
          </div>
        </el-card>
        <el-card shadow="hover">
          <template #header><span class="text-sm text-gray-500">运行时间</span></template>
          <div class="text-2xl font-bold text-blue-600">{{ status.uptime || '-' }}</div>
        </el-card>
        <el-card shadow="hover">
          <template #header><span class="text-sm text-gray-500">活跃会话</span></template>
          <div class="text-2xl font-bold text-purple-600">{{ status.active_sessions ?? 0 }}</div>
        </el-card>
        <el-card shadow="hover">
          <template #header><span class="text-sm text-gray-500">已注册模型</span></template>
          <div class="text-2xl font-bold text-orange-600">{{ status.registered_models ?? 0 }}</div>
        </el-card>
      </div>

      <!-- 配置摘要 -->
      <el-card v-if="config" shadow="hover">
        <template #header><span class="font-medium">配置摘要</span></template>
        <el-descriptions :column="2" border>
          <el-descriptions-item
            v-for="(value, key) in config"
            :key="key"
            :label="key"
          >
            {{ typeof value === 'object' ? JSON.stringify(value) : value }}
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 无数据 -->
      <el-empty
        v-if="!status && !config && !loading"
        description="无法获取系统状态，请确认后端服务已启动"
      />
    </el-skeleton>
  </div>
</template>
