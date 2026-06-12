<script setup>
/**
 * ChatInput — 消息输入组件。
 *
 * 文本输入框 + 发送/停止按钮 + Agent 模式切换 + 深度思考切换。
 * 支持从编辑重发回填内容。
 */
import { ref, watch, inject, computed } from 'vue'
import { Promotion, MagicStick, Cpu } from '@element-plus/icons-vue'

const emit = defineEmits(['send'])

// 从父组件注入 store 引用
const chatStore = inject('chatStore')

const inputText = ref('')
const agentEnabled = ref(false)
const deepThinking = ref(false)

// 监听编辑内容回填
watch(
  () => chatStore?.editingContent,
  (content) => {
    if (content) {
      inputText.value = content
      chatStore?.clearEditing()
    }
  },
)

const placeholder = computed(() => {
  const parts = []
  if (agentEnabled.value) parts.push('Agent')
  if (deepThinking.value) parts.push('思考')
  if (parts.length) return `${parts.join(' + ')} 模式... (Enter 发送, Shift+Enter 换行)`
  return '输入消息... (Enter 发送, Shift+Enter 换行)'
})

function handleSend() {
  const text = inputText.value.trim()
  if (!text) return
  emit('send', text, {
    enable_memory: true,
    enable_tools: true,
    enable_rag: agentEnabled.value,
    enable_agent: agentEnabled.value,
    enable_thinking: deepThinking.value,
  })
  inputText.value = ''
}

function toggleAgent() {
  agentEnabled.value = !agentEnabled.value
}

function toggleDeepThinking() {
  deepThinking.value = !deepThinking.value
}

function handleStop() {
  chatStore?.stopStreaming()
}

function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}
</script>

<template>
  <div class="chat-input border-t border-gray-200 bg-white p-4">
    <!-- 功能开关栏 -->
    <div class="flex items-center gap-2 mb-2.5">
      <!-- Agent 模式按钮 -->
      <button
        class="toggle-btn inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-200 select-none"
        :class="
          agentEnabled
            ? 'bg-blue-50 text-blue-600 border border-blue-300 shadow-sm'
            : 'bg-gray-50 text-gray-500 border border-gray-200 hover:bg-gray-100'
        "
        @click="toggleAgent"
        :disabled="chatStore?.isStreaming"
        title="Agent 模式：自动规划执行 · 工具调用 · RAG"
      >
        <el-icon :size="14"><Cpu /></el-icon>
        <span>Agent</span>
        <span
          class="on-badge inline-flex items-center justify-center w-4 h-4 rounded-full text-[10px] font-bold transition-all duration-200"
          :class="agentEnabled ? 'bg-blue-500 text-white' : 'bg-gray-300 text-white'"
        >{{ agentEnabled ? 'ON' : 'OFF' }}</span>
      </button>

      <!-- 深度思考按钮 -->
      <button
        class="toggle-btn inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-200 select-none"
        :class="
          deepThinking
            ? 'bg-purple-50 text-purple-600 border border-purple-300 shadow-sm'
            : 'bg-gray-50 text-gray-500 border border-gray-200 hover:bg-gray-100'
        "
        @click="toggleDeepThinking"
        :disabled="chatStore?.isStreaming"
        title="深度思考：模型输出内部推理过程"
      >
        <el-icon :size="14"><MagicStick /></el-icon>
        <span>深度思考</span>
        <span
          class="on-badge inline-flex items-center justify-center w-4 h-4 rounded-full text-[10px] font-bold transition-all duration-200"
          :class="deepThinking ? 'bg-purple-500 text-white' : 'bg-gray-300 text-white'"
        >{{ deepThinking ? 'ON' : 'OFF' }}</span>
      </button>
    </div>

    <!-- 输入区域 -->
    <div class="flex items-end gap-2">
      <el-input
        v-model="inputText"
        type="textarea"
        :autosize="{ minRows: 1, maxRows: 6 }"
        :placeholder="placeholder"
        :disabled="chatStore?.isStreaming"
        @keydown="handleKeydown"
      />
      <!-- 流式中：停止按钮 -->
      <el-button
        v-if="chatStore?.isStreaming"
        type="danger"
        @click="handleStop"
      >
        停止
      </el-button>
      <!-- 正常：发送按钮 -->
      <el-button
        v-else
        type="primary"
        :icon="Promotion"
        :disabled="!inputText.trim()"
        @click="handleSend"
      >
        发送
      </el-button>
    </div>
  </div>
</template>

<style scoped>
.toggle-btn:active:not(:disabled) {
  transform: scale(0.96);
}
</style>
