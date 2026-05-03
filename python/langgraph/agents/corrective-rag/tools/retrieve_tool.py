from langchain_community.vectorstores import Chroma
from models.EM import embedding

CHROMA_DIR = "index/chroma"


def retriever():
    vectorstore = Chroma(persist_directory=CHROMA_DIR, embedding_function=embedding)
    return vectorstore.as_retriever(search_kwargs={"k": 3})
