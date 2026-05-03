from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_experimental.text_splitter import SemanticChunker
from models.EM import embedding

CHROMA_DIR = "index/chroma"


def _chroma():
    return Chroma(persist_directory=CHROMA_DIR, embedding_function=embedding)


def list_indexed_docs():
    store = _chroma()
    results = store.get(include=["metadatas"])
    names = {m.get("source_filename") for m in results["metadatas"] if m.get("source_filename")}
    return sorted(names)


def indexer(file, filename, replace_doc=None):
    store = _chroma()

    if replace_doc:
        store.delete(where={"source_filename": replace_doc})

    docs = PyMuPDFLoader(file).load()
    splits = SemanticChunker(
        embedding,
        breakpoint_threshold_type="percentile",
        breakpoint_threshold_amount=95,
    ).split_documents(docs)

    for split in splits:
        split.metadata["source_filename"] = filename

    store.add_documents(splits)
