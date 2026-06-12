<script setup>
/**
 * ChatView — 聊天主页面。
 *
 * 消息列表 + 输入框。SessionList 由 ChatLayout 直接包含。
 */
import { onMounted, nextTick, ref, watch, provide } from 'vue'
import { useRoute } from 'vue-router'
import { useChatStore } from '@/stores/chat'
import ChatInput from '@/components/chat/ChatInput.vue'
import MessageBubble from '@/components/chat/MessageBubble.vue'
import StreamingMessage from '@/components/chat/StreamingMessage.vue'

const chatStore = useChatStore()
const route = useRoute()
const messagesContainer = ref(null)

// 注入给子组件使用
provide('chatStore', chatStore)

/** 滚动到底部 */
function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

/** 发送消息 */
function handleSend(content, options) {
  chatStore.sendMessage(content, options)
}

/** 编辑消息 */
function handleEdit(idx) {
  chatStore.editMessage(idx)
}

// 监听消息变化自动滚动
watch(
  () => chatStore.messages.length,
  () => scrollToBottom(),
)
watch(
  () => chatStore.streamingContent,
  () => scrollToBottom(),
)

// 路由参数变化时加载会话
watch(
  () => route.params.sessionId,
  (sessionId) => {
    if (sessionId) {
      chatStore.setCurrentSession(sessionId)
    }
  },
  { immediate: true },
)

onMounted(() => {
  chatStore.fetchSessions()
})
</script>

<template>
  <div class="chat-view flex flex-col h-full">
    <!-- 消息列表 -->
    <div ref="messagesContainer" class="flex-1 overflow-y-auto px-6 py-4">
      <!-- 空状态 -->
      <div
        v-if="!chatStore.messages.length && !chatStore.isStreaming"
        class="flex flex-col items-center justify-center h-full text-gray-400"
      >
        <div class="text-5xl mb-4">💬</div>
        <h3 class="text-lg font-medium">AI Chat</h3>
        <p class="text-sm mt-2">开始一段新对话</p>
      </div>

      <!-- 消息列表 -->
      <MessageBubble
        v-for="(msg, idx) in chatStore.messages"
        :key="idx"
        :role="msg.role"
        :content="msg.content"
        :index="idx"
        :thinking="msg.thinking || ''"
        :plan="msg.plan || []"
        :recovery-actions="msg.recovery_actions || []"
        :tool-calls="msg.tool_calls || []"
        @edit="handleEdit"
      />

      <!-- 流式消息 -->
      <StreamingMessage
        v-if="chatStore.isStreaming && chatStore.streamingContent"
        :content="chatStore.streamingContent"
      />

      <!-- 加载中 -->
      <div
        v-if="chatStore.isLoading && !chatStore.streamingContent"
        class="flex justify-start mb-4"
      >
        <div class="bg-white border border-gray-200 rounded-2xl rounded-bl-sm px-4 py-3 text-sm text-gray-400">
          思考中...
        </div>
      </div>
    </div>

    <!-- 输入框 -->
    <ChatInput @send="handleSend" />
  </div>
</template>
