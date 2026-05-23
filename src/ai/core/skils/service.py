"""Skill 发现、入库和工具挂载。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.ai.core.tools.types import ToolCallRequest, ToolCallResult, ToolDefinition
from src.ai.storage import Skill, SkillRepository, get_session

from .loader import SkillLoader
from .renderer import SkillRenderer
from .types import SkillDefinition


class SkillService:
    """Skill 核心服务。"""

    def __init__(
        self,
        *,
        loader: SkillLoader | None = None,
        renderer: SkillRenderer | None = None,
    ) -> None:
        self._loader = loader or SkillLoader()
        self._renderer = renderer or SkillRenderer()

    def discover_and_sync(self) -> list[Skill]:
        """发现本地 Skill 并同步到数据库。"""
        definitions = self._loader.discover()
        synced: list[Skill] = []
        with get_session() as session:
            repo = SkillRepository(session)
            for definition in definitions:
                synced.append(
                    repo.upsert_discovered(
                        skill_key=definition.skill_key,
                        display_name=definition.display_name,
                        description=definition.description,
                        version=definition.version,
                        source_path=str(definition.source_path),
                        capabilities=definition.capabilities,
                        metadata={
                            "prompt": definition.prompt,
                            "input_schema": definition.input_schema,
                            **definition.metadata,
                        },
                    )
                )
        return synced

    def list_enabled(self) -> list[Skill]:
        """列出启用的 Skill。"""
        with get_session() as session:
            return SkillRepository(session).get_enabled()

    def load_definition_from_record(self, skill: Skill) -> SkillDefinition:
        """从数据库记录还原 SkillDefinition。"""
        metadata = skill.get_metadata()
        prompt = str(metadata.get("prompt") or "")
        input_schema = metadata.get("input_schema") or {
            "type": "object",
            "properties": {"input": {"type": "string"}},
        }
        return SkillDefinition(
            skill_key=skill.skill_key,
            display_name=skill.display_name,
            description=skill.description or skill.skill_key,
            version=skill.version,
            source_path=Path(skill.source_path or ""),
            prompt=prompt,
            capabilities=skill.get_capabilities(),
            input_schema=input_schema,
            metadata={key: value for key, value in metadata.items() if key not in {"prompt", "input_schema"}},
        )

    def tool_definitions(self) -> list[ToolDefinition]:
        """把启用 Skill 转换为统一工具定义。"""
        return [self._to_tool_definition(self.load_definition_from_record(skill)) for skill in self.list_enabled()]

    def _to_tool_definition(self, definition: SkillDefinition) -> ToolDefinition:
        async def handler(request: ToolCallRequest) -> ToolCallResult:
            variables: dict[str, Any] = {
                "input": request.arguments.get("input", ""),
                "arguments": request.arguments,
                **request.arguments,
            }
            rendered = self._renderer.render(definition.prompt, variables)
            return ToolCallResult(
                tool_name=request.tool_name,
                content=rendered,
                structured_content={
                    "skill_key": definition.skill_key,
                    "source_path": str(definition.source_path),
                    "capabilities": definition.capabilities,
                },
            )

        return ToolDefinition(
            name=definition.tool_name,
            display_name=definition.display_name or definition.skill_key,
            description=definition.description,
            source_type="skill",
            source_id=definition.skill_key,
            input_schema=definition.input_schema,
            permissions=[],
            handler=handler,
            metadata={
                "skill_key": definition.skill_key,
                "source_path": str(definition.source_path),
                "capabilities": definition.capabilities,
                **definition.metadata,
            },
        )


skill_service = SkillService()
