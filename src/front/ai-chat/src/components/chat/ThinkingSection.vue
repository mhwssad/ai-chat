<script setup>
/**
 * ThinkingSection — Agent 思考过程展示组件。
 *
 * 展示 Agent 的分析/规划过程，支持折叠/展开。
 * 包含计划步骤列表，流式进行中时自动展开。
 */
import { ref, computed, watch } from 'vue'
import MarkdownIt from 'markdown-it'
import { ArrowDown, ArrowRight, Loading } from '@element-plus/icons-vue'

const props = defineProps({
  thinkingContent: { type: String, default: '' },
  planSteps: { type: Array, default: () => [] },
  isStreaming: { type: Boolean, default: false },
  recoveryActions: { type: Array, default: () => [] },
})

const collapsed = ref(false)

// 流式进行中时自动展开
watch(
  () => props.isStreaming,
  (streaming) => {
    if (streaming) {
      collapsed.value = false
    }
  },
  { immediate: true },
)

const hasContent = computed(
  () =>
    props.thinkingContent ||
    (props.planSteps && props.planSteps.length > 0) ||
    (props.recoveryActions && props.recoveryActions.length > 0),
)

const md = new MarkdownIt({ html: false, breaks: true, linkify: true })
const renderedThinking = computed(() => md.render(props.thinkingContent || ''))

/** 恢复操作的友好标签 */
function actionLabel(action) {
  const labels = {
    retry: '重试',
    fallback: '切换备选工具',
    replan: '重新规划',
    ask_user: '等待用户指导',
    retry_failed: '重试失败',
    fallback_failed: '备选也失败',
  }
  return labels[action.action] || action.action
}
</script>

<template>
  <div v-if="hasContent" class="thinking-section mb-3">
    <!-- 折叠/展开 标题栏 -->
    <button
      class="flex items-center gap-2 w-full text-left px-3 py-2 rounded-t-lg transition-colors duration-200 select-none"
      :class="
        isStreaming
          ? 'bg-amber-50 border border-amber-200 text-amber-700'
          : 'bg-gray-50 border border-gray-200 text-gray-600 hover:bg-gray-100'
      "
      @click="collapsed = !collapsed"
    >
      <!-- 图标：流式时显示加载动画 -->
      <el-icon v-if="isStreaming" class="animate-spin" :size="14">
        <Loading />
      </el-icon>
      <el-icon v-else :size="14">
        <ArrowDown v-if="!collapsed" />
        <ArrowRight v-else />
      </el-icon>

      <span class="text-xs font-medium">
        {{ isStreaming ? '分析需求 & 制定计划...' : 'Agent 执行计划' }}
      </span>

      <!-- 计划步骤进度 (非流式时显示) -->
      <span
        v-if="!isStreaming && planSteps.length"
        class="text-[10px] ml-auto opacity-60"
      >
        {{ planSteps.length }} 个步骤
      </span>
    </button>

    <!-- 展开内容 -->
    <Transition name="collapse">
      <div
        v-show="!collapsed"
        class="border border-t-0 border-gray-200 rounded-b-lg px-3 py-2 bg-white overflow-hidden"
      >
        <!-- 思考内容 (Markdown) -->
        <div
          v-if="thinkingContent"
          class="thinking-content prose prose-sm max-w-none text-gray-600 mb-3"
          v-html="renderedThinking"
        ></div>

        <!-- 计划步骤列表 -->
        <div v-if="planSteps && planSteps.length" class="plan-steps">
          <div class="text-xs font-medium text-gray-500 mb-2">执行步骤</div>
          <div
            v-for="step in planSteps"
            :key="step.step"
            class="flex items-start gap-2 py-1.5 border-b border-gray-100 last:border-0"
          >
            <span
              class="inline-flex items-center justify-center w-5 h-5 rounded-full text-[10px] font-bold flex-shrink-0 mt-0.5"
              :class="isStreaming ? 'bg-amber-100 text-amber-600' : 'bg-blue-100 text-blue-600'"
            >
              {{ step.step }}
            </span>
            <div class="flex-1 min-w-0">
              <div v-if="step.title" class="text-xs font-medium text-gray-700 leading-tight">
                {{ step.title }}
              </div>
              <div class="text-[11px] text-gray-500 leading-tight">
                {{ step.description }}
              </div>
            </div>
          </div>
        </div>

        <!-- 恢复/重试日志 -->
        <div v-if="recoveryActions && recoveryActions.length" class="recovery-log mt-2">
          <div class="text-xs font-medium text-orange-600 mb-1.5">恢复操作</div>
          <div
            v-for="(action, idx) in recoveryActions"
            :key="idx"
            class="flex items-start gap-2 py-1 text-[11px] border-b border-orange-50 last:border-0"
          >
            <span class="flex-shrink-0 mt-0.5 text-orange-500">&#8626;</span>
            <div class="min-w-0">
              <span class="font-medium text-gray-600">{{ action.tool_name }}</span>
              <span class="text-gray-400"> — </span>
              <span
                class="text-xs"
                :class="{
                  'text-green-600': action.action === 'retry',
                  'text-blue-600': action.action === 'fallback',
                  'text-orange-600': action.action === 'replan',
                  'text-purple-600': action.action === 'ask_user',
                }"
              >
                {{ actionLabel(action) }}
              </span>
              <span v-if="action.fallback_tool" class="text-gray-400">
                → {{ action.fallback_tool }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.collapse-enter-active,
.collapse-leave-active {
  transition: all 0.2s ease;
  max-height: 500px;
  overflow: hidden;
}

.collapse-enter-from,
.collapse-leave-to {
  max-height: 0;
  opacity: 0;
}

.thinking-content :deep(p) {
  margin: 0.25em 0;
  font-size: 0.825rem;
}

.thinking-content :deep(ul),
.thinking-content :deep(ol) {
  margin: 0.25em 0;
  padding-left: 1.25em;
}

.thinking-content :deep(strong) {
  color: #374151;
}
</style>
