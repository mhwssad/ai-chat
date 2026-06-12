<script setup>
/**
 * MessageBubble — 消息气泡组件。
 *
 * 区分用户/助手消息，支持 Markdown 渲染。
 * 用户消息支持编辑重发。
 * 助手消息支持 Agent 思考过程展示。
 */
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'
import { Edit } from '@element-plus/icons-vue'
import ThinkingSection from './ThinkingSection.vue'

const props = defineProps({
  role: { type: String, required: true },
  content: { type: String, default: '' },
  index: { type: Number, default: -1 },
  thinking: { type: String, default: '' },
  plan: { type: Array, default: () => [] },
  recoveryActions: { type: Array, default: () => [] },
  toolCalls: { type: Array, default: () => [] },
})

const emit = defineEmits(['edit'])

const md = new MarkdownIt({ html: false, breaks: true, linkify: true })

const renderedContent = computed(() => md.render(props.content || ''))

const isUser = computed(() => props.role === 'user')

const hasThinking = computed(
  () => props.thinking || (props.plan && props.plan.length > 0) || (props.recoveryActions && props.recoveryActions.length > 0),
)

/** 是否为工具调用消息（内容以 > 开头的工具块引用） */
const isToolOnly = computed(
  () => !isUser.value && props.content && props.content.startsWith('> ') && (props.toolCalls && props.toolCalls.length > 0),
)
</script>

<template>
  <div class="message-bubble flex mb-4" :class="isUser ? 'justify-end' : 'justify-start'">
    <div class="group max-w-[80%] relative">
      <!-- Agent 思考过程 (仅历史消息) -->
      <ThinkingSection
        v-if="!isUser && hasThinking"
        :thinking-content="thinking"
        :plan-steps="plan"
        :recovery-actions="recoveryActions"
        :is-streaming="false"
      />
      <div
        class="rounded-2xl px-4 py-3 text-sm leading-relaxed"
        :class="
          isUser
            ? 'bg-blue-500 text-white rounded-br-sm'
            : 'bg-white text-gray-800 border border-gray-200 rounded-bl-sm'
        "
      >
        <!-- 用户消息：纯文本 -->
        <div v-if="isUser" class="whitespace-pre-wrap">{{ content }}</div>

        <!-- 助手消息：Markdown 渲染 -->
        <div v-else class="prose prose-sm max-w-none" v-html="renderedContent"></div>

        <!-- 工具调用数量标签 -->
        <div
          v-if="toolCalls && toolCalls.length"
          class="flex items-center gap-1 mt-2 pt-2 border-t border-gray-100"
        >
          <span class="text-[10px] text-gray-400">
            ⚙ {{ toolCalls.length }} 个工具
          </span>
          <span
            v-for="(tc, i) in toolCalls.slice(0, 3)"
            :key="i"
            class="text-[10px] text-gray-500 bg-gray-50 px-1.5 py-0.5 rounded"
          >
            {{ (tc.name || '').replace(/^mcp__/, '').replace(/__/g, '/') }}
          </span>
          <span
            v-if="toolCalls.length > 3"
            class="text-[10px] text-gray-400"
          >
            +{{ toolCalls.length - 3 }}
          </span>
        </div>
      </div>

      <!-- 用户消息编辑按钮 (hover 显示) -->
      <button
        v-if="isUser && index >= 0"
        class="edit-btn absolute -top-2 right-0 bg-white border border-gray-200 rounded-full w-7 h-7 flex items-center justify-center shadow-sm opacity-0 transition-opacity hover:bg-gray-50"
        title="编辑重发"
        @click="emit('edit', index)"
      >
        <el-icon style="font-size: 13px; color: #666;"><Edit /></el-icon>
      </button>
    </div>
  </div>
</template>

<style scoped>
.prose :deep(pre) {
  background: #f5f5f5;
  border-radius: 6px;
  padding: 12px;
  overflow-x: auto;
}

.prose :deep(code) {
  font-size: 0.85em;
}

/* 工具调用块引用样式 */
.prose :deep(blockquote) {
  border-left: 2px solid #e5e7eb;
  padding: 2px 0 2px 10px;
  margin: 4px 0;
  color: #6b7280;
  font-size: 0.8rem;
  background: #f9fafb;
  border-radius: 0 4px 4px 0;
}

.prose :deep(blockquote code) {
  background: #f3f4f6;
  padding: 0 3px;
  border-radius: 2px;
  font-size: 0.75rem;
}

.group:hover .edit-btn {
  opacity: 1;
}
</style>
