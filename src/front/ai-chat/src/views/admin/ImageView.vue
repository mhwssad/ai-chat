<script setup>
/**
 * ImageView — 图像管理。
 *
 * 生成图像、查看列表、删除。
 */
import { onMounted, ref } from 'vue'
import PageHeader from '@/components/common/PageHeader.vue'
import * as imageApi from '@/api/image'

const images = ref([])
const loading = ref(false)
const generateDialogVisible = ref(false)
const generateForm = ref({ prompt: '', model: '', size: '1024x1024', n: 1 })

onMounted(fetchImages)

async function fetchImages() {
  loading.value = true
  try {
    const { data } = await imageApi.listImages()
    images.value = data
  } finally {
    loading.value = false
  }
}

async function generateImage() {
  await imageApi.generateImage(generateForm.value)
  generateDialogVisible.value = false
  await fetchImages()
}

async function deleteImage(filename) {
  await imageApi.deleteImage(filename)
  await fetchImages()
}
</script>

<template>
  <div>
    <PageHeader title="图像管理" subtitle="AI 图像生成和管理" />

    <el-card shadow="hover">
      <template #header>
        <div class="flex items-center justify-between">
          <span class="font-medium">图像列表</span>
          <el-button type="primary" size="small" @click="generateDialogVisible = true">生成图像</el-button>
        </div>
      </template>
      <el-table :data="images" v-loading="loading" stripe>
        <el-table-column prop="filename" label="文件名" show-overflow-tooltip />
        <el-table-column prop="prompt" label="提示词" show-overflow-tooltip />
        <el-table-column prop="model" label="模型" width="160" />
        <el-table-column prop="size" label="尺寸" width="120" />
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-popconfirm title="确认删除?" @confirm="deleteImage(row.filename)">
              <template #reference>
                <el-button text size="small" type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 生成对话框 -->
    <el-dialog v-model="generateDialogVisible" title="生成图像" width="500">
      <el-form label-width="80px">
        <el-form-item label="提示词"><el-input v-model="generateForm.prompt" type="textarea" :rows="4" /></el-form-item>
        <el-form-item label="模型"><el-input v-model="generateForm.model" placeholder="可选" /></el-form-item>
        <el-form-item label="尺寸">
          <el-select v-model="generateForm.size">
            <el-option label="1024x1024" value="1024x1024" />
            <el-option label="512x512" value="512x512" />
            <el-option label="256x256" value="256x256" />
          </el-select>
        </el-form-item>
        <el-form-item label="数量"><el-input-number v-model="generateForm.n" :min="1" :max="10" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="generateDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="generateImage">生成</el-button>
      </template>
    </el-dialog>
  </div>
</template>
