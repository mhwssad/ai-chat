<script setup>
/**
 * ChatInput — 消息输入组件。
 *
 * 文本输入框 + 发送/停止按钮 + 深度思考模式切换。
 * 支持从编辑重发回填内容。
 */
import { ref, watch, inject } from 'vue'
import { Promotion, MagicStick } from '@element-plus/icons-vue'

const emit = defineEmits(['send'])

// 从父组件注入 store 引用
const chatStore = inject('chatStore')

const inputText = ref('')
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

function handleSend() {
  const text = inputText.value.trim()
  if (!text) return
  emit('send', text, {
    enable_memory: true,               // 记忆始终开启
    enable_tools: true,                // 工具始终开启
    enable_rag: deepThinking.value,    // RAG 由开关控制
    enable_agent: deepThinking.value,  // Agent 模式由开关控制
  })
  inputText.value = ''
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
    <!-- 深度思考模式切换 -->
    <div class="flex items-center gap-2 mb-2.5">
      <button
        class="deep-toggle inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-200 select-none"
        :class="
          deepThinking
            ? 'bg-blue-50 text-blue-600 border border-blue-300 shadow-sm'
            : 'bg-gray-50 text-gray-500 border border-gray-200 hover:bg-gray-100'
        "
        @click="toggleDeepThinking"
        :disabled="chatStore?.isStreaming"
      >
        <el-icon :size="14">
          <MagicStick />
        </el-icon>
        <span>深度思考</span>
        <span
          class="inline-flex items-center justify-center w-4 h-4 rounded-full text-[10px] font-bold transition-all duration-200"
          :class="
            deepThinking
              ? 'bg-blue-500 text-white'
              : 'bg-gray-300 text-white'
          "
        >
          {{ deepThinking ? 'ON' : 'OFF' }}
        </span>
      </button>

      <span class="text-[11px] text-gray-400 transition-opacity duration-200" :class="deepThinking ? 'opacity-70' : 'opacity-40'">
        {{ deepThinking ? '已开启 · Agent 自主分析执行' : '开启 Agent 自动规划执行（含 RAG）' }}
      </span>
    </div>

    <!-- 输入区域 -->
    <div class="flex items-end gap-2">
      <el-input
        v-model="inputText"
        type="textarea"
        :autosize="{ minRows: 1, maxRows: 6 }"
        :placeholder="deepThinking ? 'Agent 模式中... (Enter 发送, Shift+Enter 换行)' : '输入消息... (Enter 发送, Shift+Enter 换行)'"
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
.deep-toggle:active:not(:disabled) {
  transform: scale(0.96);
}
</style>
