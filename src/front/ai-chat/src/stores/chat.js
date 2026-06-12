/**
 * 聊天状态管理 — 会话列表、消息历史、流式响应。
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as chatApi from '@/api/chat'
import * as sessionApi from '@/api/sessions'

export const useChatStore = defineStore('chat', () => {
  /* ── 状态 ── */
  const sessions = ref([])
  const currentSessionId = ref(null)
  const messages = ref([])
  const isLoading = ref(false)
  const isStreaming = ref(false)
  const streamingContent = ref('')
  const editingContent = ref('')
  // Agent 模式状态
  const thinkingContent = ref('')
  const planSteps = ref([])
  const recoveryActions = ref([])
  // 流式期间的工具调用追踪
  const streamingToolCalls = ref([])
  const pendingToolName = ref('')  // 当前正在执行的工具名

  /** 当前的 AbortController，用于取消流式请求 */
  let abortController = null

  /* ── 计算属性 ── */
  const currentSession = computed(() =>
    sessions.value.find((s) => s.session_id === currentSessionId.value),
  )

  /* ── 会话管理 ── */

  /** 加载会话列表 */
  async function fetchSessions() {
    try {
      const { data } = await sessionApi.listSessions({ limit: 50 })
      sessions.value = data
    } catch {
      // 错误已在拦截器中处理
    }
  }

  /** 切换当前会话 */
  async function setCurrentSession(sessionId) {
    currentSessionId.value = sessionId
    messages.value = []
    streamingContent.value = ''
    thinkingContent.value = ''
    planSteps.value = []
    recoveryActions.value = []
    streamingToolCalls.value = []
    pendingToolName.value = ''
    editingContent.value = ''

    // 加载会话历史消息
    if (sessionId) {
      try {
        const { data } = await sessionApi.getMessages(sessionId)
        messages.value = data.map((m) => ({
          role: m.role,
          content: m.content,
        }))
      } catch {
        // 保持空消息列表
      }
    }
  }

  /** 创建新会话（本地占位，首次消息后后端会创建真实会话） */
  function newSession() {
    currentSessionId.value = null
    messages.value = []
    streamingContent.value = ''
    thinkingContent.value = ''
    planSteps.value = []
    recoveryActions.value = []
    streamingToolCalls.value = []
    pendingToolName.value = ''
    editingContent.value = ''
  }

  /** 删除会话 */
  async function removeSession(sessionId) {
    await sessionApi.deleteSession(sessionId)
    sessions.value = sessions.value.filter((s) => s.session_id !== sessionId)
    if (currentSessionId.value === sessionId) {
      newSession()
    }
  }

  /* ── 消息发送 ── */

  /** 发送消息（流式） */
  async function sendMessage(content, options = {}) {
    // 添加用户消息
    messages.value.push({ role: 'user', content })

    isLoading.value = true
    isStreaming.value = true
    streamingContent.value = ''
    thinkingContent.value = ''
    planSteps.value = []
    recoveryActions.value = []
    streamingToolCalls.value = []
    pendingToolName.value = ''

    // 创建 AbortController
    abortController = new AbortController()

    try {
      const payload = {
        message: content,
        ...(currentSessionId.value ? { session_id: currentSessionId.value } : {}),
        ...options,
      }

      const response = await chatApi.chatStream(payload, abortController.signal)
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let currentEventType = 'message'  // 提取到循环外部，防止跨 chunk 丢失

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const text = decoder.decode(value, { stream: true })
        // 解析 SSE 事件
        for (const line of text.split('\n')) {
          if (line.startsWith('event: ')) {
            currentEventType = line.slice(7).trim()
            continue
          }
          if (!line.startsWith('data: ')) continue
          const raw = line.slice(6).trim()
          if (raw === '[DONE]') break
          try {
            const event = JSON.parse(raw)
            if (!event.type) event.type = currentEventType
            handleStreamEvent(event)
          } catch {
            streamingContent.value += raw
          }
        }
      }

      // 流式结束，将流式内容合并到消息列表
      if (streamingContent.value && !abortController.signal.aborted) {
        messages.value.push({
          role: 'assistant',
          content: streamingContent.value,
        })
      }
    } catch (e) {
      if (e.name === 'AbortError') {
        // 用户主动停止 — 保留已收到的内容和工具调用信息
        if (streamingContent.value || streamingToolCalls.value.length > 0) {
          let stopContent = streamingContent.value || ''
          // 标记被中断的工具
          if (pendingToolName.value) {
            const shortName = pendingToolName.value
              .replace(/^mcp__/, '')
              .replace(/__/g, ' / ')
            stopContent += `\n> ⚠️ 调用 \`${shortName}\` 被中断\n`
          }
          stopContent += '\n\n*[已停止]*'
          messages.value.push({
            role: 'assistant',
            content: stopContent,
            tool_calls: streamingToolCalls.value,
          })
        }
      } else {
        messages.value.push({
          role: 'assistant',
          content: '抱歉，请求出错了，请重试。',
        })
      }
    } finally {
      isLoading.value = false
      isStreaming.value = false
      streamingContent.value = ''
      thinkingContent.value = ''
      planSteps.value = []
      recoveryActions.value = []
      streamingToolCalls.value = []
      pendingToolName.value = ''
      abortController = null
      // 刷新会话列表
      await fetchSessions()
    }
  }

  /** 停止流式输出 */
  function stopStreaming() {
    if (abortController) {
      abortController.abort()
    }
  }

  /** 处理 SSE 事件 */
  function handleStreamEvent(event) {
    if (event.type === 'token') {
      streamingContent.value += event.content || event.data || ''
    } else if (event.type === 'thinking') {
      thinkingContent.value += event.content || ''
    } else if (event.type === 'plan_complete') {
      planSteps.value = event.plan || []
    } else if (event.type === 'recovery_action') {
      recoveryActions.value = [
        ...recoveryActions.value,
        {
          tool_name: event.tool_name,
          action: event.action,
          attempt: event.attempt,
          fallback_tool: event.fallback_tool,
          error: event.error,
          timestamp: Date.now(),
        },
      ]
    } else if (event.type === 'session') {
      if (event.session_id && !currentSessionId.value) {
        currentSessionId.value = event.session_id
      }
    } else if (event.type === 'tool_call') {
      const shortName = (event.name || '')
        .replace(/^mcp__/, '')
        .replace(/__/g, ' / ')
      streamingContent.value += `\n> ⚙️ 调用 \`${shortName}\`\n`
      streamingToolCalls.value = [
        ...streamingToolCalls.value,
        { name: event.name || '', args_preview: event.args_preview || '' },
      ]
      pendingToolName.value = event.name || ''
    } else if (event.type === 'tool_result') {
      const preview = (event.result || '').slice(0, 120)
      streamingContent.value += `> ✓ 返回: ${preview}${preview.length >= 120 ? '…' : ''}\n`
      pendingToolName.value = ''  // 工具执行完成
    } else if (event.type === 'done') {
      // 保存会话完成事件的元数据
      const hasTools = event.tool_calls && event.tool_calls.length > 0
      const toolNames = hasTools
        ? event.tool_calls.map((t) =>
            (t.name || '')
              .replace(/^mcp__/, '')
              .replace(/__/g, ' / ')
          )
        : []

      if (streamingContent.value) {
        // 有流式内容时正常追加
        const finalToolCalls = event.tool_calls && event.tool_calls.length > 0
          ? event.tool_calls
          : streamingToolCalls.value
        messages.value.push({
          role: 'assistant',
          content: streamingContent.value,
          context_sources: event.context_sources || null,
          tool_calls: finalToolCalls,
          iterations: event.iterations || 0,
          plan: event.plan || [],
          thinking: thinkingContent.value || '',
          recovery_actions: recoveryActions.value || [],
        })
      } else if (hasTools) {
        // 仅工具调用无文本回复时，显示工具执行摘要
        const finalToolCalls = event.tool_calls && event.tool_calls.length > 0
          ? event.tool_calls
          : streamingToolCalls.value
        messages.value.push({
          role: 'assistant',
          content: `> ✓ 已调用: ${toolNames.join(', ')}\n> 共执行 ${toolNames.length} 个工具`,
          tool_calls: finalToolCalls,
          iterations: event.iterations || 0,
          plan: event.plan || [],
          thinking: thinkingContent.value || '',
          recovery_actions: recoveryActions.value || [],
        })
      }
      streamingContent.value = ''
      thinkingContent.value = ''
      // 如果还没有添加 assistant 消息, 添加错误消息
      if (streamingContent.value) {
        messages.value.push({
          role: 'assistant',
          content: streamingContent.value + `\n\n*错误: ${event.error || '未知错误'}*`,
        })
        streamingContent.value = ''
      } else if (!messages.value.length || messages.value[messages.value.length - 1].role !== 'assistant') {
        messages.value.push({
          role: 'assistant',
          content: `抱歉，请求出错了: ${event.error || '请重试。'}`,
        })
      }
    }
  }

  /* ── 编辑重发 ── */

  /** 编辑指定索引的消息，删除该消息及之后的所有消息 */
  function editMessage(idx) {
    if (idx < 0 || idx >= messages.value.length) return
    const msg = messages.value[idx]
    if (msg.role !== 'user') return
    editingContent.value = msg.content
    messages.value = messages.value.slice(0, idx)
  }

  /** 清除编辑内容 */
  function clearEditing() {
    editingContent.value = ''
  }

  return {
    sessions,
    currentSessionId,
    messages,
    isLoading,
    isStreaming,
    streamingContent,
    thinkingContent,
    planSteps,
    recoveryActions,
    editingContent,
    currentSession,
    fetchSessions,
    setCurrentSession,
    newSession,
    removeSession,
    sendMessage,
    stopStreaming,
    editMessage,
    clearEditing,
  }
})
