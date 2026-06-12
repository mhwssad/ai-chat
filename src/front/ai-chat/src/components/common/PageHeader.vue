<script setup>
/**
 * PageHeader — 通用页面标题组件。
 */
defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
})
</script>

<template>
  <div class="page-header mb-6">
    <h1 class="text-xl font-semibold text-gray-800">{{ title }}</h1>
    <p v-if="subtitle" class="mt-1 text-sm text-gray-500">{{ subtitle }}</p>
  </div>
</template>
