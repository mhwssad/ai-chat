/**
 * 系统状态管理 — 运行状态、配置摘要。
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as systemApi from '@/api/system'

export const useSystemStore = defineStore('system', () => {
  /* ── 状态 ── */
  const status = ref(null)
  const config = ref(null)
  const loading = ref(false)

  /** 获取系统运行状态 */
  async function fetchStatus() {
    loading.value = true
    try {
      const { data } = await systemApi.getStatus()
      status.value = data
    } catch {
      // 错误已在拦截器中处理
    } finally {
      loading.value = false
    }
  }

  /** 获取系统配置摘要 */
  async function fetchConfig() {
    try {
      const { data } = await systemApi.getConfig()
      config.value = data
    } catch {
      // 错误已在拦截器中处理
    }
  }

  return {
    status,
    config,
    loading,
    fetchStatus,
    fetchConfig,
  }
})
