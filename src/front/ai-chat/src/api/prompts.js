/**
 * 提示词 API — CRUD、渲染、版本管理。
 */
import client from './client'

/** 获取提示词列表 */
export const listPrompts = (params) =>
  client.get('/prompts', { params })

/** 创建提示词 */
export const createPrompt = (data) => client.post('/prompts', data)

/** 获取提示词详情 */
export const getPrompt = (key) => client.get(`/prompts/${key}`)

/** 更新提示词 */
export const updatePrompt = (key, data) =>
  client.put(`/prompts/${key}`, data)

/** 删除提示词 */
export const deletePrompt = (key) => client.delete(`/prompts/${key}`)

/** 渲染提示词 */
export const renderPrompt = (data) => client.post('/prompts/render', data)

/** 获取版本列表 */
export const listVersions = (key) =>
  client.get(`/prompts/${key}/versions`)

/** 获取指定版本 */
export const getVersion = (key, version) =>
  client.get(`/prompts/${key}/versions/${version}`)

/** 回滚到指定版本 */
export const rollback = (key, data) =>
  client.post(`/prompts/${key}/rollback`, data)
