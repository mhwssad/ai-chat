"""Agent 自我反思循环 — 执行完成后自检，发现不足则自动重试或补充。

职责：
1. 评估 Agent 执行结果的完整性、准确性和意图满足度
2. 根据评估结果决定是否需要补充工具调用或改进回答
3. 封装"执行→评估→改进"循环，支持最大反思轮次配置
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from src.ai.config.logging_setup import get_logger

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
    from langchain_core.messages import BaseMessage

logger = get_logger(__name__)


class ReflectionVerdict(str, Enum):
    """反思评估结论。"""

    PASS = "pass"  # 结果充分，无需改进
    INCOMPLETE = "incomplete"  # 结果不完整，需要补充
    INACCURATE = "inaccurate"  # 结果可能不准确，需要修正
    OFF_TOPIC = "off_topic"  # 偏离用户意图，需要重新聚焦


@dataclass
class ReflectionAssessment:
    """单次反思评估结果。"""

    verdict: ReflectionVerdict
    completeness: float  # 完整性评分 0~1
    accuracy: float  # 准确性评分 0~1
    intent_alignment: float  # 意图满足度 0~1
    reasoning: str  # 评估理由
    suggestions: list[str] = field(default_factory=list)  # 改进建议
    needs_tool_call: bool = False  # 是否需要补充工具调用
    tool_suggestions: list[str] = field(default_factory=list)  # 建议的工具


@dataclass
class ReflectionResult:
    """反思循环最终结果。"""

    rounds_completed: int  # 实际执行了多少轮反思
    assessments: list[ReflectionAssessment]  # 每轮评估结果
    final_verdict: ReflectionVerdict  # 最终结论
    improved: bool  # 是否进行了改进
    extra_tokens: int = 0  # 反思过程额外消耗的 token


# 反思评估系统提示词
_REFLECTION_SYSTEM_PROMPT = """\
你是一个严格的回答质量评审员。你需要评估 AI 助手的回答质量，从三个维度打分：

1. **完整性**（0~1）：回答是否充分覆盖了用户问题的各个方面？是否遗漏了关键信息？
2. **准确性**（0~1）：回答中的事实是否正确？推理是否合乎逻辑？
3. **意图满足度**（0~1）：回答是否真正解决了用户的实际问题？

评估规则：
- 如果三个维度都 >= 0.8，判定为 PASS（结果充分，无需改进）
- 如果完整性 < 0.8，判定为 INCOMPLETE
- 如果准确性 < 0.8，判定为 INACCURATE
- 如果意图满足度 < 0.6，判定为 OFF_TOPIC

你必须以严格的 JSON 格式输出，不要包含其他文字：
```json
{
  "verdict": "pass|incomplete|inaccurate|off_topic",
  "completeness": 0.0,
  "accuracy": 0.0,
  "intent_alignment": 0.0,
  "reasoning": "评估理由",
  "suggestions": ["改进建议1", "改进建议2"],
  "needs_tool_call": false,
  "tool_suggestions": []
}
```

当判定为 INCOMPLETE 时，如果需要调用工具来补充信息：
- 设置 needs_tool_call 为 true
- 在 tool_suggestions 中列出建议使用的工具名称
"""

_REFLECTION_USER_TEMPLATE = """\
请评估以下回答的质量：

**用户原始问题**：
{user_question}

**AI 助手的回答**：
{assistant_response}

**对话上下文摘要**：
{context_summary}

请严格按照 JSON 格式输出评估结果。"""


class ReflectionLoop:
    """自我反思循环 — 封装"执行→评估→改进"循环。

    在 Agent 完成初步执行后，调用 LLM 对结果进行自我评估。
    如果评估发现不足，则追加反思消息到对话中，触发新一轮 LLM 推理。

    Args:
        llm: 用于评估的 LLM 实例（可与 Agent 主 LLM 相同）。
        max_rounds: 最大反思轮次（默认 2）。
        score_threshold: 通过阈值，所有维度 >= 此值才算 PASS（默认 0.8）。
    """

    def __init__(
        self,
        *,
        llm: BaseChatModel,
        max_rounds: int = 2,
        score_threshold: float = 0.8,
    ) -> None:
        self._llm = llm
        self._max_rounds = max_rounds
        self._score_threshold = score_threshold

    async def assess(
        self,
        *,
        user_question: str,
        assistant_response: str,
        context_summary: str = "",
    ) -> ReflectionAssessment:
        """对单次回答进行质量评估。

        Args:
            user_question: 用户的原始问题。
            assistant_response: AI 助手的回答。
            context_summary: 对话上下文摘要（可选）。

        Returns:
            评估结果。
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        messages: list[BaseMessage] = [
            SystemMessage(content=_REFLECTION_SYSTEM_PROMPT),
            HumanMessage(
                content=_REFLECTION_USER_TEMPLATE.format(
                    user_question=user_question,
                    assistant_response=assistant_response[:2000],  # 截断过长回答
                    context_summary=context_summary[:500],
                )
            ),
        ]

        try:
            response = await self._llm.ainvoke(messages)
            return self._parse_assessment(response.content)
        except Exception as e:
            logger.warning("反思评估失败，默认通过: error=%s", str(e))
            return ReflectionAssessment(
                verdict=ReflectionVerdict.PASS,
                completeness=1.0,
                accuracy=1.0,
                intent_alignment=1.0,
                reasoning=f"评估失败，默认通过: {e}",
            )

    def build_reflection_message(self, assessment: ReflectionAssessment) -> str:
        """根据评估结果构建反思提示消息，追加到对话中触发改进。

        Args:
            assessment: 评估结果。

        Returns:
            反思提示消息文本。
        """
        parts: list[str] = [
            "【自我反思】之前的回答质量评估结果：",
            f"- 完整性: {assessment.completeness:.1f}/1.0",
            f"- 准确性: {assessment.accuracy:.1f}/1.0",
            f"- 意图满足度: {assessment.intent_alignment:.1f}/1.0",
            f"- 评估结论: {assessment.verdict.value}",
            f"- 理由: {assessment.reasoning}",
        ]

        if assessment.suggestions:
            parts.append("- 改进建议:")
            for s in assessment.suggestions:
                parts.append(f"  • {s}")

        parts.append("\n请根据以上评估改进你的回答。")

        if assessment.needs_tool_call and assessment.tool_suggestions:
            tools = ", ".join(assessment.tool_suggestions)
            parts.append(f"建议使用以下工具补充信息: {tools}")

        return "\n".join(parts)

    def should_continue(self, assessment: ReflectionAssessment) -> bool:
        """判断是否需要继续反思。

        Args:
            assessment: 当前评估结果。

        Returns:
            True 表示需要继续反思改进。
        """
        return assessment.verdict != ReflectionVerdict.PASS

    @property
    def max_rounds(self) -> int:
        """最大反思轮次。"""
        return self._max_rounds

    @staticmethod
    def _parse_assessment(raw_content: str) -> ReflectionAssessment:
        """解析 LLM 输出的评估结果。

        Args:
            raw_content: LLM 返回的原始文本。

        Returns:
            解析后的评估结果。
        """
        import json
        import re

        # 尝试提取 JSON 块
        json_match = re.search(r"```json\s*(.*?)\s*```", raw_content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # 尝试直接解析整个内容
            json_str = raw_content.strip()

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning("反思评估 JSON 解析失败，默认通过: content=%s", raw_content[:200])
            return ReflectionAssessment(
                verdict=ReflectionVerdict.PASS,
                completeness=1.0,
                accuracy=1.0,
                intent_alignment=1.0,
                reasoning="JSON 解析失败，默认通过",
            )

        # 解析 verdict 枚举
        verdict_str = data.get("verdict", "pass")
        try:
            verdict = ReflectionVerdict(verdict_str)
        except ValueError:
            verdict = ReflectionVerdict.PASS

        return ReflectionAssessment(
            verdict=verdict,
            completeness=float(data.get("completeness", 1.0)),
            accuracy=float(data.get("accuracy", 1.0)),
            intent_alignment=float(data.get("intent_alignment", 1.0)),
            reasoning=str(data.get("reasoning", "")),
            suggestions=data.get("suggestions", []),
            needs_tool_call=bool(data.get("needs_tool_call", False)),
            tool_suggestions=data.get("tool_suggestions", []),
        )
