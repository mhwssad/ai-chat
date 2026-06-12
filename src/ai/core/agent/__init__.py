"""Agent 子系统 — 基于 LangGraph StateGraph 的自主任务执行。

核心组件：
- AgentOrchestrator: 编排 ReAct 循环（推理 → 工具调用 → 观察）
- ReflectionLoop: 自我反思循环（执行 → 评估 → 改进）
- AgentRouter: 多 Agent 路由（分析意图 → 分发给专业 Agent）
- AgentHandoff: Agent 间任务交接协议
- AgentTeam: 多 Agent 团队编排（编排者/辩论模式）
- GraphState: LangGraph 图状态定义
- AgentResult / AgentStatus: 执行结果类型

注意：子模块按需导入（from src.ai.core.agent.X import Y），
不在 __init__.py 中预加载，避免启动时触发 langgraph 冷导入链。
"""
