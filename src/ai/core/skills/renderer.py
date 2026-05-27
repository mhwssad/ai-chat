"""Skill 指令模板渲染 — $ARGUMENTS 替换、!`command` 动态执行。"""

import logging
import re
import subprocess

logger = logging.getLogger(__name__)


class SkillRenderer:
    """渲染 Skill 指令模板。"""

    def render(self, template: str, *, arguments: str = "") -> str:
        """渲染模板：$ARGUMENTS 替换 → !`command` 执行。

        Args:
            template: SKILL.md 正文模板。
            arguments: 用户输入的完整参数字符串（/command 后面的内容）。

        Returns:
            渲染后的字符串。
        """
        result = self._substitute_arguments(template, arguments)
        result = self._execute_commands(result)
        return result

    @staticmethod
    def _substitute_arguments(template: str, arguments: str) -> str:
        """替换 $ARGUMENTS[n]、$ARGUMENTS、$0、$1... 占位符。"""
        parts = arguments.split()

        # 先替换 $ARGUMENTS[n]（更具体的模式优先）
        def _replace_indexed(match: re.Match) -> str:
            idx = int(match.group(1))
            return parts[idx] if idx < len(parts) else ""

        result = re.sub(r"\$ARGUMENTS\[(\d+)\]", _replace_indexed, template)

        # 再替换 $ARGUMENTS（完整参数）
        result = result.replace("$ARGUMENTS", arguments)

        # 最后替换 $0、$1、$2...（位置参数，倒序避免 $1 先匹配 $10）
        for i in range(len(parts) - 1, -1, -1):
            result = result.replace(f"${i}", parts[i])

        return result

    @staticmethod
    def _execute_commands(template: str) -> str:
        """执行 !`command` 动态命令并替换为 stdout。"""
        def _run(match: re.Match) -> str:
            cmd = match.group(1)
            try:
                proc = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True, timeout=30,
                )
                return proc.stdout.strip()
            except subprocess.TimeoutExpired:
                logger.warning("动态命令超时: %s", cmd)
                return f"[命令超时: {cmd}]"
            except Exception as exc:
                logger.warning("动态命令执行失败: %s — %s", cmd, exc)
                return f"[命令失败: {exc}]"

        return re.sub(r"!`([^`]+)`", _run, template)
