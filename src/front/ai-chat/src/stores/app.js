/**
 * 应用全局状态 — 侧边栏折叠、主题等。
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  /** 聊天布局侧边栏是否折叠 */
  const chatSidebarCollapsed = ref(false)

  /** 管理布局侧边栏是否折叠 */
  const adminSidebarCollapsed = ref(false)

  /** 切换聊天侧边栏 */
  function toggleChatSidebar() {
    chatSidebarCollapsed.value = !chatSidebarCollapsed.value
  }

  /** 切换管理侧边栏 */
  function toggleAdminSidebar() {
    adminSidebarCollapsed.value = !adminSidebarCollapsed.value
  }

  return {
    chatSidebarCollapsed,
    adminSidebarCollapsed,
    toggleChatSidebar,
    toggleAdminSidebar,
  }
})
