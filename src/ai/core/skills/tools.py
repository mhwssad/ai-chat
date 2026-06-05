"""技能工具 — 提供 slash 命令技能执行能力。"""

from langchain_core.tools import BaseTool, StructuredTool


def create_skill_tool(skill_service) -> BaseTool:
    """工厂函数：创建绑定了 SkillService 的 skill 工具。"""

    async def skill(name: str, arguments: str = "") -> str:
        """执行指定技能，返回渲染后的指令内容。

        Args:
            name: 技能名称。
            arguments: 传给技能的参数。
        """
        try:
            return skill_service.activate(name, arguments=arguments)
        except Exception as exc:
            return f"技能执行失败: {exc}"

    return StructuredTool.from_function(
        coroutine=skill,
        name="skill",
    )


def register_skill_tools(registry, skill_service) -> None:
    """将技能工具注册到工具注册表。

    Args:
        registry: 工具注册表实例。
        skill_service: 技能服务实例。
    """
    from src.ai.core.tools.types import ToolMeta

    tool_obj = create_skill_tool(skill_service)
    registry.register(
        tool_obj,
        meta=ToolMeta(source_type="skill", display_name="skill", essential=True),
    )
