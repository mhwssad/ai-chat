from src.ai_chat.llm import chat_factory
from src.ai_chat.config import settings
from src.ai_chat.prompts.chat import chat_prompt


def get_chat_chain(model_name: str | None = None):
    llm = chat_factory.get_client(model_name or settings.model_name)
    return chat_prompt | llm
