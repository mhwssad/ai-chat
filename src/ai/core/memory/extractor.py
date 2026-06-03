"""从对话文本中自动提取值得记忆的信息。

支持两种模式：
1. 快速模式：纯正则匹配，适合低延迟场景
2. 增强模式：正则筛选 + LLM 精确判断，适合高质量提取
"""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING

from .types import MemoryType, MemoryWriteRequest, generate_memory_name

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

logger = logging.getLogger(__name__)

# 各类型的关键词模式：(正则, 基础置信度)
_PATTERNS: dict[MemoryType, list[tuple[str, float]]] = {
    "user": [
        (r"我(?:习惯|偏好|喜欢|常用|通常|一般)", 0.8),
        (r"I prefer|I usually|my preference|I like", 0.8),
        (r"不要(?:用|做|写)|don't|never|avoid", 0.7),
        (r"请(?:用|做|写)|please use|always use", 0.6),
        (r"我是|我的角色|I am a|I'm a", 0.7),
    ],
    "feedback": [
        (r"不要(?:这样|那样|这么)|不对|错误|别|stop|wrong", 0.8),
        (r"应该是|应该用|should be|should use", 0.75),
        (r"下次注意|以后记得|next time|from now on", 0.85),
        (r"这样(?:不对|不行|不好)|this is wrong|not right", 0.8),
        (r"请(?:不要|别再)|please don't|make sure", 0.8),
    ],
    "project": [
        (r"正在(?:做|开发|实现)|working on|currently|doing", 0.7),
        (r"(?:完成|上线|发布)了|done|finished|released|deployed", 0.75),
        (r"还没(?:做|开始|完成)|pending|not yet|TODO", 0.65),
        (r"(?:bug|issue|问题|错误|crash|故障)", 0.6),
        (r"(?:项目|分支|版本|release|branch|version)", 0.55),
        (r"(?:截止|deadline|周四|周五|下周一|本周)", 0.7),
    ],
    "reference": [
        (r"(?:链接|地址|文档|dashboard|board|panel)", 0.6),
        (r"(?:grafana|jira|linear|slack|github|docs)\.", 0.7),
        (r"(?:http|https)://\S+", 0.5),
        (r"(?:仓库|repository|repo)\s+(?:在|is at|at)", 0.65),
        (r"(?:跟踪|追踪|tracked in|managed in)", 0.65),
    ],
}


class MemoryExtractor:
    """从对话文本中提取值得记忆的信息。

    支持两种模式：
    - extract(): 快速模式，纯正则提取
    - aextract_with_llm(): 增强模式，正则筛选 + LLM 精确判断

    Args:
        llm: 用于增强模式的 LLM 实例。
        prompt_service: 提示词服务（从 DB 获取提示词模板）。
    """

    def __init__(self, llm: BaseChatModel, prompt_service: object) -> None:
        self._llm = llm
        self._prompt_service = prompt_service
        self._compiled: dict[str, list[tuple[re.Pattern, float]]] = {
            key: [
                (re.compile(pattern, re.IGNORECASE), score)
                for pattern, score in patterns
            ]
            for key, patterns in _PATTERNS.items()
        }
        self._extract_chain = None

    def _get_extract_chain(self):
        """延迟构建 LLM 提取链。"""
        if self._extract_chain is None:
            from src.ai.utils.llm_utils import build_llm_chain

            system_prompt = self._get_template_content("memory.extract_system")
            human_template = self._get_template_content("memory.extract_human")
            self._extract_chain = build_llm_chain(
                self._llm, system_prompt, human_template
            )
        return self._extract_chain

    def _get_template_content(self, prompt_key: str) -> str:
        """从 prompt_service 获取模板原始内容。"""
        template = self._prompt_service.get_template(prompt_key)  # type: ignore[attr-defined]
        if template is None:
            logger.warning("DB 中未找到 %s 模板", prompt_key)
            return ""
        return template.template

    def extract(self, text: str) -> list[MemoryWriteRequest]:
        """快速模式：纯正则提取候选记忆。"""
        candidates: list[tuple[float, MemoryWriteRequest]] = []
        lines = text.split("\n")

        for line in lines:
            line = line.strip()
            if len(line) < 10:
                continue

            best_type, best_score = self._detect_type(line)
            if best_type is None or best_score < 0.5:
                continue

            confidence = self._boost_confidence(line, best_score)
            if confidence < 0.5:
                continue

            description = line[:120].replace("\n", " ")
            name = generate_memory_name(best_type, line)

            request = MemoryWriteRequest(
                content=line,
                memory_type=best_type,
                name=name,
                description=description,
                metadata={"source": "auto", "confidence": confidence},
            )
            candidates.append((confidence, request))

        seen_names: set[str] = set()
        unique: list[MemoryWriteRequest] = []
        candidates.sort(key=lambda c: c[0], reverse=True)
        for _, req in candidates:
            if req.name not in seen_names:
                seen_names.add(req.name)  # type: ignore[arg-type]
                unique.append(req)

        return unique[:10]

    async def aextract_with_llm(self, text: str) -> list[MemoryWriteRequest]:
        """增强模式：LLM 提取高质量记忆。"""
        try:
            lines = text.split("\n")
            formatted_lines = []
            for i, line in enumerate(lines):
                if line.strip():
                    formatted_lines.append(f"[消息#{i}] {line.strip()}")
            formatted_text = "\n".join(formatted_lines)

            chain = self._get_extract_chain()
            result = await chain.ainvoke({"text": formatted_text})

            items = self._parse_llm_result(result)

            requests = []
            for item in items:
                if not item.get("content") or not item.get("memory_type"):
                    continue

                memory_type = item["memory_type"]
                if memory_type not in ("user", "feedback", "project", "reference"):
                    continue

                name = generate_memory_name(memory_type, item["content"])
                confidence = float(item.get("confidence", 0.7))

                request = MemoryWriteRequest(
                    content=item["content"],
                    memory_type=memory_type,
                    name=name,
                    description=item.get("description", item["content"][:120]),
                    metadata={"source": "llm", "confidence": confidence},
                )
                requests.append(request)

            logger.info("LLM 提取完成：从对话中提取了 %d 条记忆", len(requests))
            return requests

        except Exception:
            logger.warning("LLM 提取失败，回退到快速模式", exc_info=True)
            return self.extract(text)

    def _parse_llm_result(self, result: str) -> list[dict]:
        """解析 LLM 返回的 JSON 结果。"""
        json_match = re.search(r"\[.*\]", result, re.DOTALL)
        if not json_match:
            return []

        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            logger.warning("LLM 返回的 JSON 解析失败")
            return []

    def _detect_type(self, text: str) -> tuple[MemoryType | None, float]:
        """检测文本最匹配的记忆类型。"""
        best_type: MemoryType | None = None
        best_score = 0.0

        for memory_type, patterns in self._compiled.items():
            for pattern, base_score in patterns:
                if pattern.search(text) and base_score > best_score:
                    best_type = memory_type  # type: ignore[assignment]
                    best_score = base_score

        return best_type, best_score

    def _boost_confidence(self, text: str, base_score: float) -> float:
        """根据文本特征提升置信度。"""
        score = base_score

        if len(text) > 50:
            score += 0.05
        if len(text) > 100:
            score += 0.05
        if re.search(r"我|我们|I |we |my |our ", text, re.IGNORECASE):
            score += 0.1

        return min(score, 1.0)
