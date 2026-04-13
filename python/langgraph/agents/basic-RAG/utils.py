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
    "https://docs.langchain.com/oss/python/langgraph/overview",
    "https://docs.langchain.com/oss/python/langgraph/quickstart",
    "https://docs.langchain.com/oss/python/langgraph/thinking-in-langgraph",
    "https://docs.langchain.com/oss/python/langgraph/workflows-agents",
    "https://docs.langchain.com/oss/python/langgraph/agentic-rag",
    "https://docs.langchain.com/oss/python/langgraph/persistence",
    "https://docs.langchain.com/oss/python/langgraph/streaming",
    "https://docs.langchain.com/oss/python/langgraph/add-memory",
    "https://docs.langchain.com/oss/python/langgraph/interrupts",
    "https://docs.langchain.com/oss/python/langgraph/durable-execution",
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
