/**
 * TTS API — 语音合成、列表、删除。
 */
import client from './client'

/** 合成语音 */
export const synthesize = (data) => client.post('/tts/synthesize', data)

/** 获取语音列表 */
export const listTts = () => client.get('/tts')

/** 删除语音文件 */
export const deleteTts = (filename) =>
  client.delete(`/tts/${filename}`)
