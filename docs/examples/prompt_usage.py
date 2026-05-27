"""提示词模块使用示例。

演示 PromptService 的完整用法：创建模板、渲染、版本管理、列表查询。

运行: PYTHONPATH=. uv run python docs/examples/prompt_usage.py
"""


import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from src.ai.core.prompts import PromptRenderRequest, prompt_service
from src.ai.exception.prompt_exception import PromptNotFoundError, PromptRenderError


def demo_seed_defaults() -> None:
    """启动时自动写入默认模板（已存在的会跳过）。"""
    count = prompt_service.seed_defaults()
    print(f"[seed] 写入了 {count} 个默认模板")


def demo_create_template() -> None:
    """创建自定义提示词模板。"""
    tmpl = prompt_service.save_template(
        prompt_key="agent.translator",
        display_name="翻译助手",
        description="将文本翻译为指定语言",
        category="agent",
        template=(
            "# 翻译助手\n"
            "\n"
            "请将以下文本翻译为 {{ target_lang | default('英语') }}。\n"
            "\n"
            "**原文**：\n"
            "{{ input }}\n"
            "\n"
            "要求：\n"
            "- 保持语义和语气\n"
            "- 技术术语保留原文\n"
        ),
    )
    print(f"[create] 模板已创建: {tmpl.prompt_key}, 版本={tmpl.version}")


def demo_render() -> None:
    """渲染模板：传入变量，得到最终文本。"""
    result = prompt_service.render(
        PromptRenderRequest(
            prompt_key="agent.translator",
            variables={"input": "你好世界", "target_lang": "日语"},
        )
    )
    print(f"[render] key={result.prompt_key}, version={result.version}")
    print(result.content)


def demo_update_template() -> None:
    """更新模板：版本自动递增，旧版本归档到 prompt_versions 表。"""
    tmpl = prompt_service.save_template(
        prompt_key="agent.translator",
        template=(
            "# 专业翻译助手 v2\n"
            "\n"
            "请将以下文本翻译为 {{ target_lang | default('英语') }}。\n"
            "\n"
            "**原文**：\n"
            "{{ input }}\n"
            "\n"
            "要求：\n"
            "- 保持语义、语气和文化适配\n"
            "- 技术术语保留原文并附注\n"
            "- 提供两种译法供选择\n"
        ),
        change_note="增加文化适配和双译法",
    )
    print(f"[update] key={tmpl.prompt_key}, 新版本={tmpl.version}")


def demo_list_templates() -> None:
    """列出所有启用的模板。"""
    all_templates = prompt_service.list_templates()
    print(f"[list] 共 {len(all_templates)} 个启用模板:")
    for t in all_templates:
        print(f"  - {t.prompt_key} (v{t.version}, category={t.category})")

    # 按分类过滤
    agent_templates = prompt_service.list_templates(category="agent")
    print(f"[list] agent 分类下 {len(agent_templates)} 个模板")


def demo_render_memory_template() -> None:
    """渲染内置的 memory.system_prompt 模板。"""
    try:
        result = prompt_service.render(
            PromptRenderRequest(
                prompt_key="memory.system_prompt",
                variables={
                    "display_name": "MyProject",
                    "extra_guidelines": [
                        "每次回答前先检查记忆",
                        "如果用户说'忘了'，清除相关记忆",
                    ],
                    "entrypoint": "用户偏好使用 Python，不喜欢 Java。",
                },
            )
        )
        print(f"[memory] 渲染结果 (v{result.version}):")
        print(result.content)
    except PromptNotFoundError:
        print("[memory] 模板不存在（请先运行 seed_defaults）")


def demo_error_handling() -> None:
    """错误处理：模板不存在、渲染失败。"""
    # 模板不存在
    try:
        prompt_service.render(PromptRenderRequest(prompt_key="nonexistent"))
    except PromptNotFoundError as e:
        print(f"[error] 预期捕获: {e}")

    # 渲染失败（引用了不存在的变量，因为 StrictUndefined）
    try:
        prompt_service.render(
            PromptRenderRequest(
                prompt_key="agent.translator",
                variables={"input": "test"},  # 缺少 target_lang 但有 default，不会报错
            )
        )
        print("[error] target_lang 有默认值，渲染成功")
    except PromptRenderError as e:
        print(f"[error] 渲染失败: {e}")


if __name__ == "__main__":
    # 初始化数据库（建表）
    from src.ai.storage.database import init_database
    init_database()

    print("=" * 60)
    print("提示词模块使用示例")
    print("=" * 60)

    demo_seed_defaults()
    print()

    demo_create_template()
    print()

    demo_render()
    print()

    demo_update_template()
    print()

    demo_list_templates()
    print()

    demo_render_memory_template()
    print()

    demo_error_handling()
