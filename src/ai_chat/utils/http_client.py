"""兼容入口 — 保持现有 import 路径可用。

新代码请直接使用::

    from src.ai_chat.utils.http import http_client, converter_registry
"""

from src.ai_chat.utils.http import *  # noqa: F401,F403
