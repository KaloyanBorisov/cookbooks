"""
Demonstrates LangGraph's retry logic and fallback strategies.

Compatible with `langgraph dev` — the graph is compiled without a checkpointer
so the dev server can inject its own. For standalone use, see __main__ block.
"""

from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict
from langchain_openai import ChatOpenAI
from typing import Annotated, Optional
from langgraph.graph.message import AnyMessage, add_messages
from langchain_core.messages import HumanMessage, AIMessage

import random
import time

random.seed(42)


#  Graph state
# ------------------------------------------------------------------


class RetryState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    input_data: str
    processed_data: Optional[str]
    retry_count: int
    max_retries: int
    fallback_used: bool
    processing_complete: bool


#  Nodes
# ------------------------------------------------------------------


def data_preparation(state: RetryState):
    print("[PREP] Preparing data for processing")
    user_request = next(
        (m.content for m in reversed(state["messages"]) if m.type == "human"), ""
    )
    return {
        "input_data": f"complex_analysis_request:{user_request}",
        "retry_count": 0,
        "max_retries": 3,
        "fallback_used": False,
        "processing_complete": False,
    }


def unreliable_processor(state: RetryState):
    retry_count = state.get("retry_count", 0)
    input_data = state.get("input_data", "")
    print(f"[PROCESS] Attempt {retry_count + 1} — input: {input_data}")

    if random.random() < 0.95:
        print("[FAILURE] Processing failed - simulated service timeout")
        return {"processing_complete": False}

    print("[SUCCESS] Processing completed")
    return {
        "processed_data": f"PROCESSED_SUCCESSFULLY:{input_data}:timestamp_{time.time()}",
        "processing_complete": True,
    }


def retry_logic(state: RetryState):
    retry_count = state.get("retry_count", 0) + 1
    max_retries = state.get("max_retries", 3)
    input_data = state.get("input_data", "")

    print(f"[RETRY] Handling failure (retry count: {retry_count})")

    if retry_count <= max_retries:
        print(f"[RETRY] Direct retry {retry_count}/{max_retries}")
        return {"retry_count": retry_count}

    elif retry_count <= max_retries + 2:
        print("[FALLBACK A] Simplifying input and retrying")
        return {
            "input_data": input_data.replace("complex_", "simple_"),
            "retry_count": retry_count,
            "fallback_used": True,
        }

    else:
        print("[FALLBACK B] Giving up, using default result")
        return {
            "processed_data": f"PROCESSING_SKIPPED:{input_data}:used_fallback_at_{time.time()}",
            "processing_complete": True,
            "fallback_used": True,
        }


def response_generator(state: RetryState):
    processed_data = state.get("processed_data", "")
    fallback_used = state.get("fallback_used", False)

    if "PROCESSED_SUCCESSFULLY" in processed_data:
        content = "Data processing completed successfully! Your request has been fully processed."
    elif "PROCESSING_SKIPPED" in processed_data:
        content = "Data processing was skipped due to service issues, but we've provided a default response."
    else:
        content = "Data processing completed with alternative method."

    print(f"[COMPLETE] {'fallback' if fallback_used else 'success'}")
    return {"messages": [AIMessage(content=content)]}


#  Routing
# ------------------------------------------------------------------


def route_after_processing(state: RetryState):
    return "response_generator" if state.get("processing_complete") else "retry_logic"


def route_after_retry(state: RetryState):
    return "response_generator" if state.get("processing_complete") else "unreliable_processor"


#  Graph (no checkpointer — injected by langgraph dev at serve time)
# ------------------------------------------------------------------

builder = StateGraph(RetryState)

builder.add_node("data_preparation", data_preparation)
builder.add_node("unreliable_processor", unreliable_processor)
builder.add_node("retry_logic", retry_logic)
builder.add_node("response_generator", response_generator)

builder.add_edge(START, "data_preparation")
builder.add_edge("data_preparation", "unreliable_processor")
builder.add_conditional_edges(
    "unreliable_processor",
    route_after_processing,
    {"retry_logic": "retry_logic", "response_generator": "response_generator"},
)
builder.add_conditional_edges(
    "retry_logic",
    route_after_retry,
    {"unreliable_processor": "unreliable_processor", "response_generator": "response_generator"},
)
builder.add_edge("response_generator", END)

graph = builder.compile()


#  Standalone runner
# ------------------------------------------------------------------

if __name__ == "__main__":
    import sqlite3
    import uuid
    from langgraph.checkpoint.sqlite import SqliteSaver

    def run():
        print("\n[DEMO] Retry Logic and Fallback Strategies")
        print("=" * 60)

        conn = sqlite3.connect("retry_checkpoints.db", check_same_thread=False)
        saver = SqliteSaver(conn)
        saver.setup()
        g = builder.compile(checkpointer=saver)

        thread_id = f"retry-demo-{uuid.uuid4().hex[:8]}"
        cfg = {"configurable": {"thread_id": thread_id}}
        init_state = {
            "messages": [HumanMessage(content="Please analyze this complex dataset and provide insights")],
            "input_data": "",
            "processed_data": None,
            "retry_count": 0,
            "max_retries": 3,
            "fallback_used": False,
            "processing_complete": False,
        }

        result = g.invoke(init_state, cfg)
        print(f"\n[RESULT] Complete: {result.get('processing_complete')} | Fallback: {result.get('fallback_used')} | Retries: {result.get('retry_count')}")
        if result.get("messages"):
            print(f"[RESPONSE] {result['messages'][-1].content}")

    run()
