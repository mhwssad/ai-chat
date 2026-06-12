<script setup>
/**
 * ChatLayout — 聊天主布局。
 *
 * 左侧: 会话列表（可折叠）
 * 右侧: 对话区 + 输入框
 * 顶栏: 标题 + 管理入口
 */
import { ref } from 'vue'
import { RouterLink, RouterView } from 'vue-router'
import { Fold, Expand, Setting } from '@element-plus/icons-vue'
import SessionList from '@/components/chat/SessionList.vue'

const sidebarCollapsed = ref(false)
</script>

<template>
  <div class="chat-layout flex h-screen bg-gray-50">
    <!-- 左侧会话列表 -->
    <aside
      class="border-r border-gray-200 bg-white transition-all duration-300 flex flex-col"
      :class="sidebarCollapsed ? 'w-0 overflow-hidden' : 'w-64'"
    >
      <!-- 侧边栏头部 -->
      <div class="flex items-center justify-between px-4 h-14 border-b border-gray-200">
        <h2 class="text-sm font-semibold text-gray-700">会话列表</h2>
        <el-button text size="small" @click="sidebarCollapsed = true">
          <el-icon><Fold /></el-icon>
        </el-button>
      </div>

      <!-- 会话列表组件 -->
      <div class="flex-1 overflow-y-auto">
        <SessionList />
      </div>
    </aside>

    <!-- 右侧主区域 -->
    <div class="flex-1 flex flex-col min-w-0">
      <!-- 顶栏 -->
      <header class="flex items-center justify-between px-4 h-14 border-b border-gray-200 bg-white">
        <div class="flex items-center gap-2">
          <el-button
            v-if="sidebarCollapsed"
            text
            size="small"
            @click="sidebarCollapsed = false"
          >
            <el-icon><Expand /></el-icon>
          </el-button>
          <h1 class="text-base font-semibold text-gray-800">AI Chat</h1>
        </div>
        <div class="flex items-center gap-2">
          <RouterLink to="/admin">
            <el-button text size="small">
              <el-icon class="mr-1"><Setting /></el-icon>
              管理
            </el-button>
          </RouterLink>
        </div>
      </header>

      <!-- 对话区域 -->
      <main class="flex-1 overflow-hidden flex flex-col">
        <RouterView />
      </main>
    </div>
  </div>
</template>
