from dotenv import load_dotenv
load_dotenv()

import os
os.environ.setdefault("USER_AGENT", "basic-RAG/1.0")

from phoenix.otel import register
from openinference.instrumentation.langchain import LangChainInstrumentor

tracer_provider = register(
    project_name="basic-RAG",
    endpoint=os.environ["PHOENIX_COLLECTOR_ENDPOINT"] + "/v1/traces",
    headers={"api_key": os.environ["PHOENIX_API_KEY"]},
)
LangChainInstrumentor().instrument(tracer_provider=tracer_provider)

from utils import get_langgraph_docs_retriever, llm
from langchain_core.documents import Document
from typing import List
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END

retriever = get_langgraph_docs_retriever()


class GraphState(TypedDict):
    """
    Attributes:
        question: The user's question
        generation: The LLM's generation
        documents: List of helpful documents retrieved by the RAG pipeline
    """

    question: str
    generation: str
    documents: List[Document]


class InputState(TypedDict):
    question: str


from langchain_core.messages import HumanMessage


def retrieve_documents(state: GraphState):
    """
    Args:
        state (dict): The current graph state
    Returns:
        state (dict): New key added to state, documents, that contains retrieved documents
    """
    print("---RETRIEVE DOCUMENTS---")
    question = state["question"]
    documents = retriever.invoke(question)
    return {"documents": documents}


RAG_PROMPT = """You are an assistant for question-answering tasks. 
Use the following pieces of retrieved context to answer the question. 
If you don't know the answer, just say that you don't know. 
Use three sentences maximum and keep the answer concise.

Question: {question} 
Context: {context} 
Answer:"""


def generate_response(state: GraphState):
    """
    Args:
        state (dict): The current graph state
    Returns:
        state (dict): New key added to state, generation, that contains LLM generation
    """
    print("---GENERATE RESPONSE---")
    question = state["question"]
    documents = state["documents"]
    formatted_docs = "\n\n".join(doc.page_content for doc in documents)

    # Invoke our LLM with our RAG prompt
    rag_prompt_formatted = RAG_PROMPT.format(context=formatted_docs, question=question)
    generation = llm.invoke([HumanMessage(content=rag_prompt_formatted)])
    return {"generation": generation}


graph_builder = StateGraph(GraphState, input_schema=InputState)
graph_builder.add_node("retrieve_documents", retrieve_documents)
graph_builder.add_node("generate_response", generate_response)
graph_builder.add_edge(START, "retrieve_documents")
graph_builder.add_edge("retrieve_documents", "generate_response")
graph_builder.add_edge("generate_response", END)

graph = graph_builder.compile()

if __name__ == "__main__":
    result = graph.invoke({"question": "How does LangGraph handle persistence and checkpointing in multi-agent workflows?"})
    print("\nAnswer:", result["generation"].content)
