<script setup>
/**
 * SkillsView — 技能管理。
 *
 * 技能列表、详情、发现（重新扫描）。
 */
import { onMounted, ref } from 'vue'
import PageHeader from '@/components/common/PageHeader.vue'
import * as skillsApi from '@/api/skills'

const skills = ref([])
const commands = ref([])
const loading = ref(false)
const detailVisible = ref(false)
const currentSkill = ref(null)

onMounted(() => {
  fetchSkills()
  fetchCommands()
})

async function fetchSkills() {
  loading.value = true
  try {
    const { data } = await skillsApi.listSkills()
    skills.value = data
  } finally {
    loading.value = false
  }
}

async function fetchCommands() {
  try {
    const { data } = await skillsApi.getCommands()
    commands.value = data
  } catch { /* 拦截器处理 */ }
}

async function showDetail(name) {
  try {
    const { data } = await skillsApi.getSkill(name)
    currentSkill.value = data
    detailVisible.value = true
  } catch { /* 拦截器处理 */ }
}

async function discover() {
  await skillsApi.discoverSkills()
  await fetchSkills()
  await fetchCommands()
}
</script>

<template>
  <div>
    <PageHeader title="技能管理" subtitle="查看和管理技能插件" />

    <el-card shadow="hover" class="mb-6">
      <template #header>
        <div class="flex items-center justify-between">
          <span class="font-medium">可用斜杠命令</span>
          <el-button type="primary" size="small" @click="discover">重新扫描</el-button>
        </div>
      </template>
      <div v-if="commands.length" class="flex flex-wrap gap-2">
        <el-tag v-for="cmd in commands" :key="cmd.command" type="info">
          {{ cmd.command }}
        </el-tag>
      </div>
      <div v-else class="text-sm text-gray-400">暂无可用命令</div>
    </el-card>

    <el-card shadow="hover">
      <template #header><span class="font-medium">技能列表</span></template>
      <el-table :data="skills" v-loading="loading" stripe>
        <el-table-column prop="name" label="名称" width="200" />
        <el-table-column prop="description" label="描述" show-overflow-tooltip />
        <el-table-column prop="user_invocable" label="可调用" width="100">
          <template #default="{ row }">
            <el-tag :type="row.user_invocable ? 'success' : 'info'" size="small">
              {{ row.user_invocable ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button text size="small" @click="showDetail(row.name)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailVisible" title="技能详情" width="600">
      <template v-if="currentSkill">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="名称">{{ currentSkill.name }}</el-descriptions-item>
          <el-descriptions-item label="描述">{{ currentSkill.description }}</el-descriptions-item>
          <el-descriptions-item label="路径">{{ currentSkill.source_path }}</el-descriptions-item>
          <el-descriptions-item v-if="currentSkill.argument_hint" label="参数提示">{{ currentSkill.argument_hint }}</el-descriptions-item>
          <el-descriptions-item label="可调用">{{ currentSkill.user_invocable ? '是' : '否' }}</el-descriptions-item>
          <el-descriptions-item label="禁止模型调用">{{ currentSkill.disable_model_invocation ? '是' : '否' }}</el-descriptions-item>
        </el-descriptions>
      </template>
    </el-dialog>
  </div>
</template>
