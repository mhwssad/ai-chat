"""细粒度权限策略引擎 — 支持参数模式匹配和自定义策略文件。

职责：
1. 按工具类型 + 参数模式匹配权限规则
2. 敏感操作（文件删除、网络请求、代码执行）默认需确认
3. 支持用户自定义权限策略文件（JSON）
4. 与现有 PermissionChecker 集成
"""

from __future__ import annotations

import fnmatch
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.ai.config.logging_setup import get_logger
from src.ai.core.tools.permissions import PermissionLevel

logger = get_logger(__name__)


@dataclass
class PermissionRule:
    """单条权限规则。

    Attributes:
        tool_name: 工具名模式（支持 glob，如 "shell_*"）。
        param_patterns: 参数名 → 参数值模式的映射（如 {"path": "/etc/*"}）。
        level: 权限级别。
        description: 规则描述。
        priority: 优先级（数值越高越优先，默认 0）。
    """

    tool_name: str
    param_patterns: dict[str, str] = field(default_factory=dict)
    level: PermissionLevel = PermissionLevel.AUTO
    description: str = ""
    priority: int = 0

    def matches(self, tool_name: str, arguments: dict[str, Any]) -> bool:
        """检查规则是否匹配指定的工具调用。

        Args:
            tool_name: 待检查的工具名称。
            arguments: 工具参数。

        Returns:
            True 表示规则匹配。
        """
        # 工具名匹配（支持 glob）
        if not fnmatch.fnmatch(tool_name, self.tool_name):
            return False

        # 参数模式匹配
        for param_key, param_pattern in self.param_patterns.items():
            value = arguments.get(param_key)
            if value is None:
                return False
            if not fnmatch.fnmatch(str(value), param_pattern):
                return False

        return True


# 敏感操作默认策略
SENSITIVE_DEFAULTS: list[PermissionRule] = [
    # 文件删除操作始终需确认
    PermissionRule(
        tool_name="delete_file",
        level=PermissionLevel.CONFIRM,
        description="文件删除操作需要确认",
        priority=10,
    ),
    # 写入系统目录直接拒绝
    PermissionRule(
        tool_name="write_file",
        param_patterns={"path": "/etc/*"},
        level=PermissionLevel.DENY,
        description="禁止写入系统目录",
        priority=20,
    ),
    PermissionRule(
        tool_name="write_file",
        param_patterns={"path": "C:\\Windows\\*"},
        level=PermissionLevel.DENY,
        description="禁止写入 Windows 系统目录",
        priority=20,
    ),
    # Shell 命令执行需确认
    PermissionRule(
        tool_name="shell_*",
        level=PermissionLevel.CONFIRM,
        description="Shell 命令执行需要确认",
        priority=5,
    ),
    # 危险 shell 命令拒绝
    PermissionRule(
        tool_name="shell_*",
        param_patterns={"command": "rm -rf /*"},
        level=PermissionLevel.DENY,
        description="拒绝危险删除命令",
        priority=30,
    ),
    PermissionRule(
        tool_name="shell_*",
        param_patterns={"command": "format *"},
        level=PermissionLevel.DENY,
        description="拒绝格式化命令",
        priority=30,
    ),
]


@dataclass
class PolicyFile:
    """权限策略文件格式。

    JSON 文件结构：
    {
      "rules": [
        {
          "tool_name": "write_file",
          "param_patterns": {"path": "/etc/*"},
          "level": "deny",
          "description": "禁止写入系统目录",
          "priority": 20
        }
      ]
    }
    """

    rules: list[PermissionRule] = field(default_factory=list)

    @classmethod
    def from_json(cls, json_str: str) -> PolicyFile:
        """从 JSON 字符串加载策略。

        Args:
            json_str: JSON 格式的策略内容。

        Returns:
            解析后的策略文件对象。
        """
        data = json.loads(json_str)
        rules: list[PermissionRule] = []
        for rule_data in data.get("rules", []):
            level_str = rule_data.get("level", "auto")
            try:
                level = PermissionLevel(level_str)
            except ValueError:
                level = PermissionLevel.AUTO
            rules.append(
                PermissionRule(
                    tool_name=rule_data.get("tool_name", "*"),
                    param_patterns=rule_data.get("param_patterns", {}),
                    level=level,
                    description=rule_data.get("description", ""),
                    priority=rule_data.get("priority", 0),
                )
            )
        return cls(rules=rules)

    @classmethod
    def from_file(cls, path: Path) -> PolicyFile:
        """从文件加载策略。

        Args:
            path: 策略文件路径。

        Returns:
            解析后的策略文件对象。
        """
        if not path.exists():
            return cls()
        content = path.read_text(encoding="utf-8")
        try:
            return cls.from_json(content)
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("策略文件解析失败: path=%s, error=%s", path, e)
            return cls()

    def to_json(self) -> str:
        """导出为 JSON 字符串。"""
        rules_data = []
        for rule in self.rules:
            rules_data.append(
                {
                    "tool_name": rule.tool_name,
                    "param_patterns": rule.param_patterns,
                    "level": rule.level.value,
                    "description": rule.description,
                    "priority": rule.priority,
                }
            )
        return json.dumps({"rules": rules_data}, indent=2, ensure_ascii=False)


class PermissionPolicyEngine:
    """权限策略引擎 — 合并默认策略和自定义策略，按优先级匹配。

    Args:
        custom_rules: 用户自定义规则列表。
        policy_file_path: 策略文件路径（可选）。
    """

    def __init__(
        self,
        *,
        custom_rules: list[PermissionRule] | None = None,
        policy_file_path: Path | None = None,
    ) -> None:
        self._rules: list[PermissionRule] = list(SENSITIVE_DEFAULTS)

        # 加载策略文件
        if policy_file_path is not None:
            policy_file = PolicyFile.from_file(policy_file_path)
            self._rules.extend(policy_file.rules)
            logger.info(
                "从策略文件加载 %d 条规则: path=%s",
                len(policy_file.rules),
                policy_file_path,
            )

        # 加载自定义规则
        if custom_rules:
            self._rules.extend(custom_rules)

        # 按优先级降序排序
        self._rules.sort(key=lambda r: r.priority, reverse=True)

    def evaluate(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> PermissionLevel | None:
        """评估工具调用的权限级别。

        返回第一条匹配的规则的权限级别。
        如果没有规则匹配，返回 None（表示无自定义策略，由默认策略决定）。

        Args:
            tool_name: 工具名称。
            arguments: 工具参数。

        Returns:
            权限级别，或 None（无匹配规则）。
        """
        for rule in self._rules:
            if rule.matches(tool_name, arguments):
                logger.debug(
                    "策略匹配: tool=%s, rule=%s, level=%s",
                    tool_name,
                    rule.description or rule.tool_name,
                    rule.level.value,
                )
                return rule.level
        return None

    def add_rule(self, rule: PermissionRule) -> None:
        """添加自定义规则。

        Args:
            rule: 权限规则。
        """
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.priority, reverse=True)

    def remove_rule(self, tool_name: str, param_patterns: dict[str, str]) -> bool:
        """移除匹配的规则。

        Args:
            tool_name: 工具名模式。
            param_patterns: 参数模式。

        Returns:
            True 表示成功移除。
        """
        original_count = len(self._rules)
        self._rules = [
            r
            for r in self._rules
            if not (r.tool_name == tool_name and r.param_patterns == param_patterns)
        ]
        return len(self._rules) < original_count

    @property
    def rules(self) -> list[PermissionRule]:
        """获取所有规则（只读副本）。"""
        return list(self._rules)
