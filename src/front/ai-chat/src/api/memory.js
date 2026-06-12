/**
 * 记忆 API — 列表、搜索、CRUD、统计。
 */
import client from './client'

/** 获取记忆列表 */
export const listMemory = (params) =>
  client.get('/memory', { params })

/** 保存记忆 */
export const saveMemory = (data) => client.post('/memory', data)

/** 获取记忆详情 */
export const getMemory = (name) => client.get(`/memory/${name}`)

/** 删除记忆 */
export const deleteMemory = (name) => client.delete(`/memory/${name}`)

/** 禁用记忆 */
export const disableMemory = (name) =>
  client.post(`/memory/${name}/disable`)

/** 启用记忆 */
export const enableMemory = (name) =>
  client.post(`/memory/${name}/enable`)

/** 搜索记忆 */
export const searchMemory = (data) => client.post('/memory/search', data)

/** 从对话提取记忆 */
export const extractMemory = (data) => client.post('/memory/extract', data)

/** 重建记忆索引 */
export const rebuildIndex = () => client.post('/memory/rebuild-index')

/** 获取记忆统计 */
export const getStats = () => client.get('/memory/stats')
