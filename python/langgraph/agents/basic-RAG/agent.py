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
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field
from typing import List, Literal
from typing_extensions import TypedDict, Annotated

retriever = get_langgraph_docs_retriever()


# --- State ---

class GraphState(TypedDict):
    question: str
    generation: str
    documents: List[Document]
    filtered_documents: List[Document]
    messages: Annotated[List[BaseMessage], add_messages]  # conversation history


class InputState(TypedDict):
    question: str


# --- Document grader ---

class GradeDocument(BaseModel):
    score: Literal["yes", "no"] = Field(
        description="Is the document relevant to the question? 'yes' or 'no'."
    )


grader_llm = llm.with_structured_output(GradeDocument)

GRADE_PROMPT = """You are a grader assessing whether a retrieved document is relevant to a user question.

Document:
{document}

Question: {question}

If the document contains keywords or semantic meaning related to the question, grade it as relevant.
Give a binary score 'yes' or 'no'."""


# --- Prompts ---

REWRITE_PROMPT = """You are rewriting a question to improve retrieval from a vector database.

Look at the question and reason about the underlying semantic intent, then rewrite it to be more specific and retrieval-friendly.

Original question: {question}
Rewritten question:"""

RAG_PROMPT = """You are an assistant for question-answering tasks.
Use the following pieces of retrieved context to answer the question.
If you don't know the answer, just say that you don't know.
Use three sentences maximum and keep the answer concise.

Conversation history:
{history}

Question: {question}
Context: {context}
Answer:"""


# --- Nodes ---

def retrieve_documents(state: GraphState):
    print("---RETRIEVE DOCUMENTS---")
    documents = retriever.invoke(state["question"])
    return {"documents": documents}


def grade_documents(state: GraphState):
    print("---GRADE DOCUMENTS---")
    question = state["question"]
    documents = state["documents"]

    filtered = []
    for doc in documents:
        prompt = GRADE_PROMPT.format(document=doc.page_content, question=question)
        result = grader_llm.invoke([HumanMessage(content=prompt)])
        if result.score == "yes":
            print("  ✓ relevant")
            filtered.append(doc)
        else:
            print("  ✗ irrelevant, filtering out")

    return {"filtered_documents": filtered}


def rewrite_question(state: GraphState):
    print("---REWRITE QUESTION---")
    prompt = REWRITE_PROMPT.format(question=state["question"])
    response = llm.invoke([HumanMessage(content=prompt)])
    new_question = response.content
    print(f"  Rewritten: {new_question}")
    return {"question": new_question}


def generate_response(state: GraphState):
    print("---GENERATE RESPONSE---")
    question = state["question"]
    documents = state["filtered_documents"]
    formatted_docs = "\n\n".join(doc.page_content for doc in documents)

    # Format conversation history for the prompt
    history = ""
    if state.get("messages"):
        history_lines = []
        for msg in state["messages"]:
            role = "User" if isinstance(msg, HumanMessage) else "Assistant"
            history_lines.append(f"{role}: {msg.content}")
        history = "\n".join(history_lines)
    else:
        history = "No previous conversation."

    prompt = RAG_PROMPT.format(
        history=history,
        context=formatted_docs,
        question=question,
    )
    generation = llm.invoke([HumanMessage(content=prompt)])

    # Append this turn to the conversation history
    return {
        "generation": generation,
        "messages": [
            HumanMessage(content=question),
            AIMessage(content=generation.content),
        ],
    }


# --- Conditional edge ---

def decide_to_generate(state: GraphState) -> Literal["generate_response", "rewrite_question"]:
    if state["filtered_documents"]:
        print("---DECISION: relevant docs found, generating---")
        return "generate_response"
    print("---DECISION: no relevant docs, rewriting question---")
    return "rewrite_question"


# --- Graph ---

graph_builder = StateGraph(GraphState, input_schema=InputState)

graph_builder.add_node("retrieve_documents", retrieve_documents)
graph_builder.add_node("grade_documents", grade_documents)
graph_builder.add_node("rewrite_question", rewrite_question)
graph_builder.add_node("generate_response", generate_response)

graph_builder.add_edge(START, "retrieve_documents")
graph_builder.add_edge("retrieve_documents", "grade_documents")
graph_builder.add_conditional_edges("grade_documents", decide_to_generate)
graph_builder.add_edge("rewrite_question", "retrieve_documents")
graph_builder.add_edge("generate_response", END)

graph = graph_builder.compile(checkpointer=MemorySaver())

if __name__ == "__main__":
    config = {"configurable": {"thread_id": "session-1"}}

    questions = [
        "What is LangGraph?",
        "How does it handle persistence and checkpointing?",
        "Can you give an example of how to use that in a multi-agent workflow?",
    ]

    for question in questions:
        print(f"\nQ: {question}")
        result = graph.invoke({"question": question}, config=config)
        print(f"A: {result['generation'].content}")
