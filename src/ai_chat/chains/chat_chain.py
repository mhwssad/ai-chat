from typing import Optional

from src.ai_chat.config import settings
from src.ai_chat.prompts.chat import chat_prompt


def get_chat_chain(model_name: Optional[str] = None):
    llm = chat_factory.get_client(model_name or settings.model_name)
    return chat_prompt | llm
