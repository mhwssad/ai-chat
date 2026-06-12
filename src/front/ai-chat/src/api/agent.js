/**
 * Agent API — 编排运行、取消、恢复、团队模式。
 */
import client from './client'

/** 运行 Agent 编排循环 */
export const runAgent = (data) => client.post('/agent/run', data)

/** 取消运行中的 Agent */
export const cancelAgent = (data) => client.post('/agent/cancel', data)

/** 从检查点恢复 Agent */
export const resumeAgent = (data) => client.post('/agent/resume', data)

/** 编排者团队模式 */
export const teamOrchestrator = (data) =>
  client.post('/agent/team/orchestrator', data)

/** 辩论团队模式 */
export const teamDebate = (data) => client.post('/agent/team/debate', data)
