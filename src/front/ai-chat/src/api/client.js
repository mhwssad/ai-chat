/**
 * Axios 客户端实例 — 统一请求/响应处理。
 *
 * - baseURL: /api（Vite proxy 转发到后端 8000 端口）
 * - 超时: 60 秒（流式接口另行处理）
 * - 拦截器: 统一错误提示
 */
import axios from 'axios'
import { ElMessage } from 'element-plus'

const client = axios.create({
  baseURL: '/api',
  timeout: 60_000,
  headers: { 'Content-Type': 'application/json' },
})

// 请求拦截器
client.interceptors.request.use(
  (config) => config,
  (error) => Promise.reject(error),
)

// 响应拦截器 — 统一错误处理
client.interceptors.response.use(
  (response) => response,
  (error) => {
    const msg = error.response?.data?.detail || error.message || '请求失败'
    ElMessage.error(msg)
    return Promise.reject(error)
  },
)

export default client
