/**
 * RAG API — 索引文件/URL/文本/目录、搜索、文档管理。
 */
import client from './client'

/** 索引文件 */
export const indexFile = (data) => client.post('/rag/index/file', data)

/** 索引 URL */
export const indexUrl = (data) => client.post('/rag/index/url', data)

/** 索引文本 */
export const indexText = (data) => client.post('/rag/index/text', data)

/** 索引目录 */
export const indexDirectory = (data) =>
  client.post('/rag/index/directory', data)

/** 向量相似度搜索 */
export const search = (data) => client.post('/rag/search', data)

/** 混合搜索 */
export const searchHybrid = (data) => client.post('/rag/search/hybrid', data)

/** 获取文档列表 */
export const listDocuments = (params) =>
  client.get('/rag/documents', { params })

/** 删除文档 */
export const deleteDocument = (path) =>
  client.delete(`/rag/documents/${encodeURIComponent(path)}`)

/** 删除全部文档 */
export const deleteAllDocuments = () =>
  client.post('/rag/documents/delete-all')

/** 获取 RAG 统计 */
export const getStats = () => client.get('/rag/stats')
