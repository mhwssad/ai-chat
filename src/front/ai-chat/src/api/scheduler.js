/**
 * 调度器 API — 任务 CRUD、启停、日志、统计。
 */
import client from './client'

/** 创建 Cron 任务 */
export const createCron = (data) =>
  client.post('/scheduler/tasks/cron', data)

/** 创建 Interval 任务 */
export const createInterval = (data) =>
  client.post('/scheduler/tasks/interval', data)

/** 创建一次性任务 */
export const createOneShot = (data) =>
  client.post('/scheduler/tasks/one-shot', data)

/** 获取任务列表 */
export const listTasks = (params) =>
  client.get('/scheduler/tasks', { params })

/** 获取任务详情 */
export const getTask = (id) => client.get(`/scheduler/tasks/${id}`)

/** 删除任务 */
export const deleteTask = (id) =>
  client.delete(`/scheduler/tasks/${id}`)

/** 启用任务 */
export const enableTask = (id) =>
  client.post(`/scheduler/tasks/${id}/enable`)

/** 禁用任务 */
export const disableTask = (id) =>
  client.post(`/scheduler/tasks/${id}/disable`)

/** 暂停任务 */
export const pauseTask = (id) =>
  client.post(`/scheduler/tasks/${id}/pause`)

/** 恢复任务 */
export const resumeTask = (id) =>
  client.post(`/scheduler/tasks/${id}/resume`)

/** 获取任务执行日志 */
export const getTaskLogs = (id, params) =>
  client.get(`/scheduler/tasks/${id}/logs`, { params })

/** 获取调度器统计 */
export const getStats = () => client.get('/scheduler/stats')
