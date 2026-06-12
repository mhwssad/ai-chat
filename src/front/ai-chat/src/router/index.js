/**
 * 路由配置 — 前台聊天 + 后台管理双区域。
 *
 * 前台: / → ChatLayout → ChatView
 * 后台: /admin → AdminLayout → 12 个管理子页面
 */
import { createRouter, createWebHistory } from 'vue-router'

/* ── 布局 ── */
import ChatLayout from '@/layouts/ChatLayout.vue'
import AdminLayout from '@/layouts/AdminLayout.vue'

/* ── 前台页面 ── */
import ChatView from '@/views/chat/ChatView.vue'

/* ── 后台页面 ── */
import DashboardView from '@/views/admin/DashboardView.vue'
import ModelsView from '@/views/admin/ModelsView.vue'
import ToolsView from '@/views/admin/ToolsView.vue'
import SkillsView from '@/views/admin/SkillsView.vue'
import PromptsView from '@/views/admin/PromptsView.vue'
import MemoryView from '@/views/admin/MemoryView.vue'
import RagView from '@/views/admin/RagView.vue'
import SchedulerView from '@/views/admin/SchedulerView.vue'
import SessionsView from '@/views/admin/SessionsView.vue'
import AgentView from '@/views/admin/AgentView.vue'
import ImageView from '@/views/admin/ImageView.vue'
import TtsView from '@/views/admin/TtsView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    /* ── 前台聊天 ── */
    {
      path: '/',
      component: ChatLayout,
      children: [
        { path: '', name: 'chat', component: ChatView },
        { path: 'chat/:sessionId', name: 'chat-session', component: ChatView },
      ],
    },

    /* ── 后台管理 ── */
    {
      path: '/admin',
      component: AdminLayout,
      redirect: '/admin/dashboard',
      children: [
        { path: 'dashboard', name: 'admin-dashboard', component: DashboardView },
        { path: 'models', name: 'admin-models', component: ModelsView },
        { path: 'tools', name: 'admin-tools', component: ToolsView },
        { path: 'skills', name: 'admin-skills', component: SkillsView },
        { path: 'prompts', name: 'admin-prompts', component: PromptsView },
        { path: 'memory', name: 'admin-memory', component: MemoryView },
        { path: 'rag', name: 'admin-rag', component: RagView },
        { path: 'scheduler', name: 'admin-scheduler', component: SchedulerView },
        { path: 'sessions', name: 'admin-sessions', component: SessionsView },
        { path: 'agent', name: 'admin-agent', component: AgentView },
        { path: 'image', name: 'admin-image', component: ImageView },
        { path: 'tts', name: 'admin-tts', component: TtsView },
      ],
    },
  ],
})

export default router
