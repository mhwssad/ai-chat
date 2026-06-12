/**
 * 对话 API — 聊天、流式、OpenAI 兼容接口。
 */
import client from './client'

/** 非流式聊天 */
export const chat = (data) => client.post('/chat', data)

/** 流式聊天 (SSE)，返回原始 Response。signal 用于取消请求。 */
export const chatStream = (data, signal) =>
  fetch('/api/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
    signal,
  })

/** OpenAI 兼容聊天接口 */
export const chatMessages = (data) => client.post('/chat/messages', data)
