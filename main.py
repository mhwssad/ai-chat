from src.ai_chat.chains.chat_chain import get_chat_chain
from langchain_core.messages import HumanMessage
from src.ai_chat.llm.factory import chat_factory

def main():
    chat = chat_factory.get_client("minmax-2.7")
    r = chat.invoke([HumanMessage(content="你好")])
    print(r)

if __name__ == "__main__":
    main()
