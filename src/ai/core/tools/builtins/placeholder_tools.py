"""占位工具声明 — 暂未实现但可被发现的工具。"""

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, ConfigDict

from src.ai.core.tools.register import register_tool


class _PlaceholderArgs(BaseModel):
    """占位工具通用参数。"""

    model_config = ConfigDict(extra="allow")


_PLACEHOLDERS: dict[str, str] = {
    "TaskCreate": "创建新任务",
    "TaskGet": "获取任务详情",
    "TaskList": "列出所有任务",
    "TaskUpdate": "更新任务状态",
    "TaskStop": "停止运行中的后台任务",
    "TaskOutput": "获取任务执行输出",
    "Agent": "分叉子代理并行处理复杂任务",
    "CronCreate": "创建定时任务",
    "CronDelete": "删除定时任务",
    "CronList": "列出所有定时任务",
    "RemoteTrigger": "管理远程代理触发器",
    "TeamCreate": "创建团队协调多代理工作",
    "TeamDelete": "删除团队及任务目录",
    "LSP": "代码智能",
    "SendMessage": "向子代理发送消息",
}


def _make_placeholder(name: str, description: str) -> StructuredTool:
    """创建占位工具实例。"""

    async def _not_implemented(**kwargs: object) -> str:
        return f"工具 {name} 尚未实现"

    return StructuredTool.from_function(
        coroutine=_not_implemented,
        name=name,
        description=f"[占位] {description}",
        args_schema=_PlaceholderArgs,
    )


# ── 自注册 ──────────────────────────────────────────────────────────────────

for _name, _desc in _PLACEHOLDERS.items():
    register_tool(
        _make_placeholder(_name, _desc),
        source_type="builtin",
        enabled=False,
    )
