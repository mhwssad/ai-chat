from src.ai_chat.graphs.chat_agent import ChatAgent
from src.ai_chat.graphs.chat_graph import ChatGraph


def anget():
    agent = ChatAgent(model_name="minimax-m2.7")
    print(agent.invoke("你有哪些技能"))


def main():
    a = input("请输入：")
    if a == "1":
        agent = ChatAgent(model_name="minimax-m2.7")
        print(agent.invoke("你有哪些技能"))
    elif a == "2":
        agent = ChatGraph(model_name="minimax-m2.7")
        print(agent.invoke("你最喜欢什么"))


if __name__ == "__main__":
    main()
