<script setup>
/**
 * TtsView — 语音管理。
 *
 * 语音合成、列表、删除、播放。
 */
import { onMounted, ref } from 'vue'
import PageHeader from '@/components/common/PageHeader.vue'
import * as ttsApi from '@/api/tts'

const audioList = ref([])
const loading = ref(false)
const synthesizeDialogVisible = ref(false)
const synthesizeForm = ref({ text: '', voice: '', model: '' })
const currentAudio = ref(null)

onMounted(fetchList)

async function fetchList() {
  loading.value = true
  try {
    const { data } = await ttsApi.listTts()
    audioList.value = data
  } finally {
    loading.value = false
  }
}

async function synthesize() {
  await ttsApi.synthesize(synthesizeForm.value)
  synthesizeDialogVisible.value = false
  await fetchList()
}

async function deleteTts(filename) {
  await ttsApi.deleteTts(filename)
  await fetchList()
}

function playAudio(filename) {
  currentAudio.value = `/api/tts/${filename}`
}
</script>

<template>
  <div>
    <PageHeader title="语音管理" subtitle="TTS 语音合成和音频管理" />

    <!-- 播放器 -->
    <el-card v-if="currentAudio" shadow="hover" class="mb-6">
      <audio :src="currentAudio" controls class="w-full" autoplay />
    </el-card>

    <el-card shadow="hover">
      <template #header>
        <div class="flex items-center justify-between">
          <span class="font-medium">音频列表</span>
          <el-button type="primary" size="small" @click="synthesizeDialogVisible = true">语音合成</el-button>
        </div>
      </template>
      <el-table :data="audioList" v-loading="loading" stripe>
        <el-table-column prop="filename" label="文件名" show-overflow-tooltip />
        <el-table-column prop="text" label="文本" show-overflow-tooltip />
        <el-table-column prop="voice" label="声音" width="120" />
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button text size="small" type="primary" @click="playAudio(row.filename)">播放</el-button>
            <el-popconfirm title="确认删除?" @confirm="deleteTts(row.filename)">
              <template #reference>
                <el-button text size="small" type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 合成对话框 -->
    <el-dialog v-model="synthesizeDialogVisible" title="语音合成" width="500">
      <el-form label-width="80px">
        <el-form-item label="文本"><el-input v-model="synthesizeForm.text" type="textarea" :rows="6" /></el-form-item>
        <el-form-item label="声音"><el-input v-model="synthesizeForm.voice" placeholder="可选" /></el-form-item>
        <el-form-item label="模型"><el-input v-model="synthesizeForm.model" placeholder="可选" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="synthesizeDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="synthesize">合成</el-button>
      </template>
    </el-dialog>
  </div>
</template>
