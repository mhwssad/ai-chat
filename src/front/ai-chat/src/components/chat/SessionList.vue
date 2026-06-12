<script setup>
/**
 * SessionList — 会话列表侧边栏组件。
 *
 * 显示会话列表，支持新建、切换、删除。
 */
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useChatStore } from '@/stores/chat'
import { Delete, Plus, ChatDotRound } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'

const chatStore = useChatStore()
const router = useRouter()

onMounted(() => {
  chatStore.fetchSessions()
})

function handleSelect(sessionId) {
  chatStore.setCurrentSession(sessionId)
}

async function handleDelete(sessionId) {
  try {
    await ElMessageBox.confirm('确定要删除这个会话吗？删除后无法恢复。', '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    chatStore.removeSession(sessionId)
  } catch {
    // 用户取消
  }
}

function handleNew() {
  chatStore.newSession()
  router.push('/')
}

/** 格式化时间为相对时间 */
function formatTime(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  if (isNaN(date.getTime())) return dateStr
  const now = new Date()
  const diff = now - date
  const mins = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (mins < 1) return '刚刚'
  if (mins < 60) return `${mins}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days < 7) return `${days}天前`
  return date.toLocaleDateString('zh-CN')
}
</script>

<template>
  <div class="session-list flex flex-col h-full">
    <!-- 新建按钮 -->
    <div class="p-3">
      <el-button type="primary" class="w-full" @click="handleNew">
        <el-icon class="mr-1"><Plus /></el-icon>
        新建会话
      </el-button>
    </div>

    <!-- 会话列表 -->
    <div class="flex-1 overflow-y-auto px-2">
      <div
        v-for="session in chatStore.sessions"
        :key="session.session_id"
        class="session-item group px-3 py-2.5 rounded-lg cursor-pointer mb-1 transition-colors"
        :class="
          session.session_id === chatStore.currentSessionId
            ? 'bg-blue-50 text-blue-700'
            : 'hover:bg-gray-100 text-gray-700'
        "
        @click="handleSelect(session.session_id)"
      >
        <div class="flex items-center justify-between">
          <span class="text-sm font-medium truncate flex-1">
            {{ session.title || '新对话' }}
          </span>
          <el-button
            text
            size="small"
            class="delete-btn ml-1"
            @click.stop="handleDelete(session.session_id)"
          >
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
        <div class="flex items-center justify-between mt-0.5">
          <span class="text-xs opacity-60">
            <el-icon class="mr-0.5" style="font-size: 12px;"><ChatDotRound /></el-icon>
            {{ session.message_count ?? 0 }} 条消息
          </span>
          <span class="text-xs opacity-50">{{ formatTime(session.last_active_at) }}</span>
        </div>
      </div>

      <div
        v-if="!chatStore.sessions.length"
        class="text-center text-sm text-gray-400 py-12"
      >
        <el-icon class="mb-2" style="font-size: 32px; opacity: 0.3;"><ChatDotRound /></el-icon>
        <p>暂无会话</p>
        <p class="text-xs mt-1">点击上方按钮开始新对话</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.delete-btn {
  opacity: 0;
  transition: opacity 0.15s;
}
.session-item:hover .delete-btn {
  opacity: 1;
}
</style>
