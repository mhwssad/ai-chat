<script setup>
/**
 * StreamingMessage — 流式消息显示组件。
 *
 * 实时显示 SSE 流式响应内容，集成 Agent 思考过程展示。
 */
import { computed, inject } from 'vue'
import MarkdownIt from 'markdown-it'
import ThinkingSection from './ThinkingSection.vue'

const props = defineProps({
  content: { type: String, default: '' },
})

const chatStore = inject('chatStore')

const md = new MarkdownIt({ html: false, breaks: true, linkify: true })

const renderedContent = computed(() => md.render(props.content || ''))
</script>

<template>
  <div class="streaming-message flex mb-4 justify-start">
    <div class="max-w-[80%]">
      <!-- Agent 思考过程 -->
      <ThinkingSection
        v-if="chatStore"
        :thinking-content="chatStore.thinkingContent"
        :plan-steps="chatStore.planSteps"
        :recovery-actions="chatStore.recoveryActions"
        :is-streaming="chatStore.isStreaming"
      />
      <!-- 主回复内容 -->
      <div class="rounded-2xl rounded-bl-sm px-4 py-3 text-sm leading-relaxed bg-white text-gray-800 border border-gray-200">
        <div class="prose prose-sm max-w-none" v-html="renderedContent"></div>
        <span class="inline-block w-2 h-4 ml-1 bg-gray-400 animate-pulse rounded-sm" />
      </div>
    </div>
  </div>
</template>
