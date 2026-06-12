/**
 * 技能 API — 列表、发现、详情、命令。
 */
import client from './client'

/** 获取技能列表 */
export const listSkills = () => client.get('/skills')

/** 重新扫描技能目录 */
export const discoverSkills = () => client.post('/skills/discover')

/** 获取可用斜杠命令 */
export const getCommands = () => client.get('/skills/commands')

/** 获取技能详情 */
export const getSkill = (name) => client.get(`/skills/${name}`)
