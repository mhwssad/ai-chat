/**
 * 模型配置 API — 供应商、模型 CRUD、测试连接。
 */
import client from './client'

// ── 供应商 ──

/** 获取供应商列表 */
export const listProviders = () => client.get('/models/providers')

/** 创建供应商 */
export const createProvider = (data) =>
  client.post('/models/providers', data)

/** 更新供应商 */
export const updateProvider = (key, data) =>
  client.put(`/models/providers/${key}`, data)

/** 删除供应商 */
export const deleteProvider = (key) =>
  client.delete(`/models/providers/${key}`)

// ── 模型 ──

/** 获取模型列表 */
export const listModels = (params) =>
  client.get('/models', { params })

/** 创建模型 */
export const createModel = (data) => client.post('/models', data)

/** 更新模型 */
export const updateModel = (key, data) =>
  client.put(`/models/${key}`, data)

/** 删除模型 */
export const deleteModel = (key) => client.delete(`/models/${key}`)

/** 测试模型连通性 */
export const testModel = (key) => client.post(`/models/${key}/test`)
