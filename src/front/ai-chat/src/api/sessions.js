/**
 * 会话 API — 列表、详情、归档、删除、消息历史。
 */
import client from './client'

/** 获取会话列表 */
export const listSessions = (params) =>
  client.get('/sessions', { params })

/** 获取会话详情 */
export const getSession = (id) => client.get(`/sessions/${id}`)

/** 归档会话 */
export const archiveSession = (id) =>
  client.put(`/sessions/${id}/archive`)

/** 删除会话 */
export const deleteSession = (id) => client.delete(`/sessions/${id}`)

/** 获取会话消息历史 */
export const getMessages = (id) => client.get(`/sessions/${id}/messages`)
