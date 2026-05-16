"""项目配置。

继承 ``BaseSettingsConfig``，支持：
- ``get_map()``          字段名 → 环境变量名映射
- ``refresh()``          从 .env 重新加载
- ``save_to_env_file()`` 回写 .env
"""
from typing import Optional

from pydantic import SecretStr

from src.ai_chat.config.base_config import BaseSettingsConfig


class Settings(BaseSettingsConfig):
    """全局配置，从 .env 文件和环境变量自动加载。"""

    # ── 应用级 ──────────────────────────────────────────
    model_name: str = "minmax-2.7"
    request_timeout: int = 60

    # ── OpenAI ──────────────────────────────────────────
    openai_api_key: SecretStr = SecretStr("")
    openai_base_url: str = ""

    # ── Google Gemini ───────────────────────────────────
    google_api_key: SecretStr = SecretStr("")

    # ── Anthropic Claude ────────────────────────────────
    anthropic_api_key: SecretStr = SecretStr("")

    # ── Ollama ──────────────────────────────────────────
    ollama_base_url: str = "http://localhost:11434"

    # ── minmax ────────────────────────────────────────
    minmax_api_key: SecretStr = SecretStr("")
    minmax_base_url: str = "https://api.minimaxi.com/v1"

    # ── qwen ────────────────────────────────────────
    qwen_api_key: SecretStr = SecretStr("")
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # ── Memory ────────────────────────────────────────────
    memory_backend: str = "sqlite"
    memory_persist_path: str = ""
    memory_max_short_term_messages: int = 20
    memory_summary_model: str = ""
    memory_summary_token_limit: int = 1000
    memory_enable_summary: bool = True

    # ── Token 感知上下文管理 ──────────────────────────────
    # JSON 字符串，映射 model_name -> context_window_tokens
    # 示例环境变量: MODEL_CONTEXT_OVERRIDES='{"gpt-4o": 64000, "qwen2.5": 32000}'
    model_context_overrides: str = ""
    # 压缩触发阈值比例 (0.0~1.0)
    model_context_threshold: float = 0.8
    # 未注册模型的默认上下文大小
    model_default_context_size: int = 8192

    # ── 工具方法 ────────────────────────────────────────

    def get_key(self, key: SecretStr) -> Optional[SecretStr]:
        """返回密钥，空值返回 None。"""
        return key if key else None

    def masked(self, key: SecretStr) -> str:
        """API Key 脱敏输出，仅显示前后 4 位。"""
        raw = key.get_secret_value()
        if len(raw) <= 8:
            return "****"
        return f"{raw[:4]}****{raw[-4:]}"


settings = Settings()
