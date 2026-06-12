/**
 * 系统 API — 状态、配置。
 */
import client from './client'

/** 获取系统运行状态 */
export const getStatus = () => client.get('/system/status')

/** 获取系统配置摘要 */
export const getConfig = () => client.get('/system/config')
