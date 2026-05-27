"""RAG 模块使用示例。

演示文件索引、向量搜索、上下文构建、会话隔离知识库等完整流程。
索引和搜索使用 ChromaDB 持久化存储，Embedding 通过 Ollama (bge-m3) 获取。

运行: PYTHONPATH=. uv run python docs/examples/srag_usage.py
"""


import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.ai.config.model_settings import chat_model_config
from src.ai.core.models import model_registry
from src.ai.core.rag import (
    HashEmbeddings,
    RagTextSplitter,
    create_rag_service,
    rag_service,
)

# 示例文件目录
SAMPLES_DIR = r"E:\project\ai-chat\docs\examples\samples"


def _build_llm():
    """构建 LangChain BaseChatModel。"""
    builder = model_registry.get_builder("chat", chat_model_config.backend)
    return builder.build(chat_model_config)


# ── 1. 服务初始化 ──────────────────────────────────────────


def demo_rag_service_init():
    """RagService 初始化方式。"""
    print("=== 模块级单例（推荐，自动从配置解析依赖）===")
    print(f"  embeddings:  {type(rag_service._embeddings).__name__}")
    print(f"  loader:      {type(rag_service._loader).__name__}")
    print(f"  splitter:    {type(rag_service._splitter).__name__}")
    print(f"  collection:  {rag_service._base_collection}")
    print(f"  persist_dir: {rag_service._persist_dir}")
    print(f"  stats:       {rag_service.get_stats()}")
    print()


def demo_custom_service():
    """自定义参数创建服务（依赖倒置）。"""
    # 通过工厂函数覆盖部分依赖
    svc = create_rag_service(embeddings=HashEmbeddings())
    print("=== 自定义 Embeddings 服务 ===")
    print(f"  embeddings: {type(svc._embeddings).__name__}")
    print(f"  stats: {svc.get_stats()}")
    print()


# ── 2. Embedding 配置 ──────────────────────────────────────


def demo_embedding_config():
    """Embedding 配置说明。"""
    from src.ai.config.model_settings import EmbeddingModelConfig

    config = EmbeddingModelConfig()
    print("=== Embedding 配置（从 .env 加载 EMBEDDING_MODEL_*）===")
    print(f"  model_key:  {config.model_key}")
    print(f"  backend:    {config.backend}")
    print(f"  base_url:   {config.base_url}")
    print()


def demo_hash_fallback():
    """无外部模型时，HashEmbeddings 自动兜底。"""
    emb = HashEmbeddings()
    vectors = emb.embed_documents(["测试文本", "第二段文本"])
    print("=== HashEmbeddings 回退（无外部模型时自动使用）===")
    print(f"  维度:     {len(vectors[0])}")
    print(f"  向量前5: {vectors[0][:5]}")
    print()


# ── 3. 文件索引 ──────────────────────────────────────────


def demo_index_single_file():
    """索引单个 Markdown 文件。"""
    from pathlib import Path

    demo_file = Path(SAMPLES_DIR) / "demo_article.md"

    print("=== 索引单文件: demo_article.md ===")
    doc_info = rag_service.index_file(demo_file, reindex=True)
    print(f"  source_path: {doc_info.source_path}")
    print(f"  title:       {doc_info.title}")
    print(f"  chunk_count: {doc_info.chunk_count}")
    print(f"  mime_type:   {doc_info.mime_type}")
    print()


def demo_index_directory():
    """批量索引 samples 目录。"""
    print("=== 批量索引 samples/ 目录 ===")
    documents = rag_service.index_directory(
        SAMPLES_DIR,
        patterns=["**/*.md", "**/*.txt", "**/*.py", "**/*.csv"],
        reindex=True,
    )
    for doc in documents:
        print(f"  {doc.title}: {doc.chunk_count} chunks ({doc.mime_type})")
    print(f"  共索引 {len(documents)} 个文件")
    print()


# ── 4. 向量搜索 ──────────────────────────────────────────


def demo_search():
    """向量相似度搜索。"""
    queries = ["项目架构", "RAG 检索", "环境搭建"]
    for query in queries:
        print(f'=== 搜索: "{query}" ===')
        results = rag_service.search(query, top_k=3)
        if not results:
            print("  (无匹配结果)")
        for r in results:
            preview = r.content[:80].replace("\n", " ")
            print(f"  [{r.score:.4f}] {r.title} (chunk {r.chunk_index})")
            print(f"         {preview}...")
        print()


# ── 5. 上下文构建 + LLM 集成 ──────────────────────────────


def demo_build_context():
    """构建 LLM 上下文文本。"""
    query = "工具系统"
    print(f'=== 构建上下文: "{query}" ===')
    context = rag_service.build_context(query, top_k=3)
    if context:
        print(f"  上下文长度: {len(context)} 字符")
        preview = context[:300].replace("\n", "\n  ")
        print(f"  {preview}...")
    else:
        print("  (无匹配结果)")
    print()


def demo_rag_with_llm():
    """端到端：RAG 检索 → 注入 LLM 上下文 → 问答。"""
    llm = _build_llm()
    query = "这个项目支持哪些功能"

    # 1. RAG 检索上下文
    context = rag_service.build_context(query, top_k=5)
    if not context:
        print("[chat] 未检索到相关文档")
        return

    # 2. 将 RAG 上下文注入 SystemMessage
    messages = [
        SystemMessage(content=f"请根据以下参考资料回答问题。\n\n{context}"),
        HumanMessage(content=query),
    ]

    print("[chat] 发送带 RAG 上下文的请求...")
    response: AIMessage = llm.invoke(messages)
    print(f"[chat] 模型回复:")
    print(f"  {response.content[:400]}...")
    print()


# ── 6. 会话隔离知识库 ─────────────────────────────────────


def demo_session_isolation():
    """会话隔离：每个会话拥有独立的知识库。"""
    from pathlib import Path

    # 会话 A：索引 demo_article.md
    demo_file = Path(SAMPLES_DIR) / "demo_article.md"
    rag_service.index_file(demo_file, session_id="session-a")

    # 会话 B：索引 readme.txt
    readme_file = Path(SAMPLES_DIR) / "readme.txt"
    rag_service.index_file(readme_file, session_id="session-b")

    # 搜索验证隔离
    print("=== 会话隔离验证 ===")
    results_a = rag_service.search("技术", session_id="session-a", top_k=2)
    results_b = rag_service.search("readme", session_id="session-b", top_k=2)
    results_global = rag_service.search("技术", top_k=2)

    print(f"  session-a 搜索 '技术': {len(results_a)} 条结果")
    for r in results_a:
        print(f"    [{r.score:.4f}] {r.title}")
    print(f"  session-b 搜索 'readme': {len(results_b)} 条结果")
    for r in results_b:
        print(f"    [{r.score:.4f}] {r.title}")
    print(f"  全局搜索 '技术': {len(results_global)} 条结果（独立于会话）")

    # 列出所有会话
    sessions = rag_service.list_sessions()
    print(f"  活跃会话: {sessions}")

    # 清理会话
    for sid in sessions:
        rag_service.delete_session(sid)
    print(f"  已清理所有会话")
    print()


# ── 7. 文档管理 ──────────────────────────────────────────


def demo_list_and_stats():
    """列出所有已索引文件 + 统计。"""
    print("=== 已索引文件列表 ===")
    documents = rag_service.list_documents()
    for doc in documents:
        print(f"  {doc.title}: {doc.chunk_count} chunks ({doc.mime_type})")
    print(f"  共 {len(documents)} 个文件")
    print()

    stats = rag_service.get_stats()
    print("=== 向量库统计 ===")
    print(f"  total_chunks:    {stats['total_chunks']}")
    print(f"  collection_name: {stats['collection_name']}")
    print()


# ── 8. 删除操作 ──────────────────────────────────────────


def demo_delete():
    """演示删除操作。"""
    from pathlib import Path

    # 删除单个文件
    readme_path = str(Path(SAMPLES_DIR) / "readme.txt")
    print("=== 删除单文件: readme.txt ===")
    deleted = rag_service.delete_file(readme_path)
    print(f"  deleted: {deleted}")
    print()

    # 清空全部数据
    print("=== 清空全部数据 ===")
    count = rag_service.delete_all()
    print(f"  已删除 {count} 个 chunks")
    print(f"  stats: {rag_service.get_stats()}")
    print()


# ── 9. 文本切分 ──────────────────────────────────────────


def demo_splitter():
    """RagTextSplitter 文本切分。"""
    splitter = RagTextSplitter(chunk_size=200, chunk_overlap=30)

    text = (
        "AI Chat 是基于 FastAPI 的本地 AI 工作台。"
        "它提供多供应商模型调用、工具执行、MCP 协议、RAG 检索等能力。"
        "项目使用 Python 3.13，uv 管理依赖。"
    )

    print("=== 文本切分 ===")
    chunks = splitter.split(text)
    for chunk in chunks:
        print(f"  chunk {chunk.index}: {chunk.content}")
    print()


# ── 主入口 ──────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("RAG 模块示例")
    print("=" * 60)
    print()

    # 基础：初始化和配置
    demo_rag_service_init()
    demo_custom_service()
    demo_embedding_config()
    demo_hash_fallback()
    demo_splitter()

    # 核心：索引 → 搜索 → 上下文 → LLM 问答
    demo_index_single_file()
    demo_index_directory()
    demo_search()
    demo_build_context()
    demo_rag_with_llm()

    # 会话隔离
    demo_session_isolation()

    # 管理：列表 + 统计
    demo_list_and_stats()

    # 清理：删除示例数据
    demo_delete()

    print(">>> 示例结束，数据已清理 <<<")
