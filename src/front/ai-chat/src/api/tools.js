/**
 * 工具 API — 列表、详情、测试执行。
 */
import client from './client'

/** 获取工具列表 */
export const listTools = (params) =>
  client.get('/tools', { params })

/** 获取工具详情 */
export const getTool = (name) => client.get(`/tools/${name}`)

/** 测试执行工具 */
export const executeTool = (name, data) =>
  client.post(`/tools/${name}/execute`, data)
