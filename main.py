from langchain_core.prompts import MessagesPlaceholder, ChatPromptTemplate

from src.ai_chat.llm import llm_factory


def main():
    SYSTEM_PROMPT = "你是一个有帮助的 AI 助手。请用中文回答用户的问题。"

    chat_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )
    print(chat_prompt)

    provider = llm_factory.get_chat_provider("MiniMax-M2.7")
    client = provider.get_client("MiniMax-M2.7")
    chain = chat_prompt | client
    print(chain.invoke({"messages": [{"role": "user", "content": "你好"}]}))


if __name__ == "__main__":
    main()
