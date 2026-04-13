import os
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter

DB_PATH = str(Path(__file__).parent / "langgraph-docs-db")
from langchain_community.document_loaders import WebBaseLoader
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

# NOTE: Configure the LLM that you want to use
llm = ChatOpenAI(model_name="gpt-4o", temperature=0)
# llm = ChatAnthropic(model_name="claude-3-5-sonnet-20240620", temperature=0)
# llm = ChatVertexAI(model_name="gemini-1.5-flash-002", temperature=0)


# NOTE: Configure the embedding model that you want to use
embedding_model = OpenAIEmbeddings()

# NOTE: Add the documentation you want to perform RAG over
LANGGRAPH_DOCS = [
    # LangGraph core
    "https://docs.langchain.com/oss/python/langgraph/overview",
    "https://docs.langchain.com/oss/python/langgraph/quickstart",
    "https://docs.langchain.com/oss/python/langgraph/install",
    "https://docs.langchain.com/oss/python/langgraph/thinking-in-langgraph",
    "https://docs.langchain.com/oss/python/langgraph/workflows-agents",
    "https://docs.langchain.com/oss/python/langgraph/choosing-apis",
    "https://docs.langchain.com/oss/python/langgraph/graph-api",
    "https://docs.langchain.com/oss/python/langgraph/functional-api",
    "https://docs.langchain.com/oss/python/langgraph/use-graph-api",
    "https://docs.langchain.com/oss/python/langgraph/use-functional-api",
    # LangGraph agents & RAG
    "https://docs.langchain.com/oss/python/langgraph/agentic-rag",
    "https://docs.langchain.com/oss/python/langgraph/sql-agent",
    "https://docs.langchain.com/oss/python/langgraph/case-studies",
    # LangGraph memory & persistence
    "https://docs.langchain.com/oss/python/langgraph/persistence",
    "https://docs.langchain.com/oss/python/langgraph/add-memory",
    "https://docs.langchain.com/oss/python/langgraph/interrupts",
    "https://docs.langchain.com/oss/python/langgraph/durable-execution",
    "https://docs.langchain.com/oss/python/langgraph/use-time-travel",
    # LangGraph streaming & frontend
    "https://docs.langchain.com/oss/python/langgraph/streaming",
    "https://docs.langchain.com/oss/python/langgraph/ui",
    "https://docs.langchain.com/oss/python/langgraph/frontend/overview",
    "https://docs.langchain.com/oss/python/langgraph/frontend/graph-execution",
    # LangGraph deployment & tooling
    "https://docs.langchain.com/oss/python/langgraph/application-structure",
    "https://docs.langchain.com/oss/python/langgraph/use-subgraphs",
    "https://docs.langchain.com/oss/python/langgraph/observability",
    "https://docs.langchain.com/oss/python/langgraph/local-server",
    "https://docs.langchain.com/oss/python/langgraph/deploy",
    "https://docs.langchain.com/oss/python/langgraph/studio",
    "https://docs.langchain.com/oss/python/langgraph/test",
    "https://docs.langchain.com/oss/python/langgraph/pregel",
    # LangChain core concepts
    "https://docs.langchain.com/oss/python/langchain/overview",
    "https://docs.langchain.com/oss/python/langchain/quickstart",
    "https://docs.langchain.com/oss/python/langchain/install",
    "https://docs.langchain.com/oss/python/langchain/philosophy",
    "https://docs.langchain.com/oss/python/langchain/models",
    "https://docs.langchain.com/oss/python/langchain/tools",
    "https://docs.langchain.com/oss/python/langchain/agents",
    "https://docs.langchain.com/oss/python/langchain/messages",
    "https://docs.langchain.com/oss/python/langchain/runtime",
    # LangChain RAG & retrieval
    "https://docs.langchain.com/oss/python/langchain/retrieval",
    "https://docs.langchain.com/oss/python/langchain/structured-output",
    "https://docs.langchain.com/oss/python/langchain/context-engineering",
    # LangChain memory & human-in-the-loop
    "https://docs.langchain.com/oss/python/langchain/short-term-memory",
    "https://docs.langchain.com/oss/python/langchain/long-term-memory",
    "https://docs.langchain.com/oss/python/langchain/human-in-the-loop",
    "https://docs.langchain.com/oss/python/concepts/memory",
    # LangChain advanced
    "https://docs.langchain.com/oss/python/langchain/mcp",
    "https://docs.langchain.com/oss/python/langchain/guardrails",
    "https://docs.langchain.com/oss/python/langchain/streaming",
    "https://docs.langchain.com/oss/python/langchain/observability",
    "https://docs.langchain.com/oss/python/deepagents/overview",
]


# NOTE: Define a retriever
def get_langgraph_docs_retriever():
    # If there is a vectorstore at this path, early return as it is already persisted
    if os.path.exists(DB_PATH):
        vectorstore = Chroma(
            collection_name="langgraph-docs",
            embedding_function=embedding_model,
            persist_directory=DB_PATH,
        )
        count = vectorstore._collection.count()
        if count > 0:
            print(f"Loading vectorstore from disk ({count} embeddings)...")
            return vectorstore.as_retriever(lambda_mult=0)
        print("Vectorstore exists but is empty, rebuilding...")
        import shutil
        shutil.rmtree(DB_PATH)

    # Otherwise, load the documents and persist to the vectorstore
    docs = [WebBaseLoader(url).load() for url in LANGGRAPH_DOCS]
    docs_list = [item for sublist in docs for item in sublist]
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=200, chunk_overlap=0
    )
    doc_splits = text_splitter.split_documents(docs_list)
    vectorstore = Chroma(
        collection_name="langgraph-docs",
        embedding_function=embedding_model,
        persist_directory=DB_PATH,
    )
    vectorstore.add_documents(doc_splits)
    print("Vectorstore created and persisted to disk")
    return vectorstore.as_retriever(lambda_mult=0)
