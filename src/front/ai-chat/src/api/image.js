/**
 * 图像 API — 生成、列表、删除。
 */
import client from './client'

/** 生成图像 */
export const generateImage = (data) => client.post('/image/generate', data)

/** 获取图像列表 */
export const listImages = () => client.get('/image')

/** 删除图像 */
export const deleteImage = (filename) =>
  client.delete(`/image/${filename}`)
