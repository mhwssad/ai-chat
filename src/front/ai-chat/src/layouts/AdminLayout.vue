<script setup>
/**
 * AdminLayout — 后台管理布局。
 *
 * 左侧: Element Plus 可折叠侧边栏菜单
 * 顶栏: 标题 + 返回聊天
 * 内容区: <router-view />
 */
import { ref, computed } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import {
  Monitor,
  Setting,
  Grid,
  MagicStick,
  ChatDotRound,
  Memo,
  Collection,
  Timer,
  User,
  Picture,
  Microphone,
  Promotion,
  Back,
  Expand,
  Fold,
} from '@element-plus/icons-vue'

const isCollapsed = ref(false)
const route = useRoute()

const activeMenu = computed(() => route.path)

const menuItems = [
  { index: '/admin/dashboard', icon: Monitor, label: '仪表盘' },
  { index: '/admin/models', icon: Setting, label: '模型配置' },
  { index: '/admin/tools', icon: Grid, label: '工具管理' },
  { index: '/admin/skills', icon: MagicStick, label: '技能管理' },
  { index: '/admin/prompts', icon: ChatDotRound, label: '提示词模板' },
  { index: '/admin/memory', icon: Memo, label: '记忆管理' },
  { index: '/admin/rag', icon: Collection, label: 'RAG 管理' },
  { index: '/admin/scheduler', icon: Timer, label: '定时任务' },
  { index: '/admin/sessions', icon: User, label: '会话管理' },
  { index: '/admin/agent', icon: Promotion, label: 'Agent 配置' },
  { index: '/admin/image', icon: Picture, label: '图像管理' },
  { index: '/admin/tts', icon: Microphone, label: '语音管理' },
]
</script>

<template>
  <div class="admin-layout flex h-screen bg-gray-100">
    <!-- 左侧侧边栏 -->
    <aside
      class="bg-white border-r border-gray-200 transition-all duration-300 flex flex-col"
      :class="isCollapsed ? 'w-16' : 'w-56'"
    >
      <!-- Logo 区域 -->
      <div
        class="flex items-center h-14 border-b border-gray-200 px-4"
        :class="isCollapsed ? 'justify-center' : 'justify-between'"
      >
        <span v-if="!isCollapsed" class="text-base font-bold text-gray-800">
          管理后台
        </span>
        <el-button text size="small" @click="isCollapsed = !isCollapsed">
          <el-icon>
            <Fold v-if="!isCollapsed" />
            <Expand v-else />
          </el-icon>
        </el-button>
      </div>

      <!-- 导航菜单 -->
      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapsed"
        :collapse-transition="false"
        router
        class="flex-1 border-r-0"
      >
        <el-menu-item
          v-for="item in menuItems"
          :key="item.index"
          :index="item.index"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <template #title>{{ item.label }}</template>
        </el-menu-item>
      </el-menu>
    </aside>

    <!-- 右侧主区域 -->
    <div class="flex-1 flex flex-col min-w-0">
      <!-- 顶栏 -->
      <header class="flex items-center justify-between px-6 h-14 bg-white border-b border-gray-200">
        <h2 class="text-sm font-medium text-gray-600">
          {{ menuItems.find((m) => m.index === activeMenu)?.label || '管理' }}
        </h2>
        <RouterLink to="/">
          <el-button text size="small">
            <el-icon class="mr-1"><Back /></el-icon>
            返回聊天
          </el-button>
        </RouterLink>
      </header>

      <!-- 内容区 -->
      <main class="flex-1 overflow-y-auto p-6">
        <router-view />
      </main>
    </div>
  </div>
</template>
