"""
Demonstrates LangGraph's fault-tolerance with pending writes.

Compatible with `langgraph dev` — the graph is compiled without a checkpointer
so the dev server can inject its own. For standalone use, run with a checkpointer
passed explicitly (see __main__ block).
"""

from langgraph.graph import StateGraph, START, END
from langchain_core.tools import tool
from typing_extensions import TypedDict
from langchain_openai import ChatOpenAI
from typing import Annotated
from langgraph.graph.message import AnyMessage, add_messages
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.prebuilt import ToolNode

import json
import os
import time


#  Graph state
# ------------------------------------------------------------------


def merge_dicts(left: dict, right: dict) -> dict:
    if left is None:
        return right
    if right is None:
        return left
    return {**left, **right}


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    attempt_count: int
    finance_data: dict
    intermediate_results: Annotated[dict, merge_dicts]


#  Tools
# ------------------------------------------------------------------


def load_finance_data() -> dict:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(os.path.dirname(current_dir), "data", "finance_data.json")
    with open(data_path, "r") as f:
        return json.load(f)


@tool
def get_finance_data():
    """Return the dataset of company contracts (names, amounts, terms, renewals)."""
    return load_finance_data()


@tool
def multiply_by_pi(number: int):
    """Multiply a number by π."""
    return 3.14159 * number


#  LLM
# ------------------------------------------------------------------

llm = ChatOpenAI(model="gpt-4o")
tools = [get_finance_data, multiply_by_pi]
model_with_tools = llm.bind_tools(tools)
tool_node = ToolNode(tools)


#  Routing
# ------------------------------------------------------------------


def should_continue(state: State):
    last_message = state["messages"][-1]
    return "continue" if last_message.tool_calls else "end"


#  Nodes
# ------------------------------------------------------------------


def finance_assistant(state: State):
    attempt_count = state.get("attempt_count", 0) + 1
    intermediate_results = state.get("intermediate_results", {})
    has_preprocessed = "preprocessed_data" in intermediate_results
    has_analysis = "analysis_results" in intermediate_results

    user_question = next(
        (m.content for m in reversed(state["messages"]) if m.type == "human"), ""
    )

    if has_preprocessed and has_analysis:
        print(f"[INFO] finance_assistant attempt {attempt_count} - providing final response")
        prompt = f"""You are an expert financial analyst.
The data preprocessing and analysis phases have been completed.
Answer the user's question based on data already in the conversation: {user_question}
Do not make any tool calls."""
        response = llm.invoke([SystemMessage(prompt)] + state["messages"])
    else:
        print(f"[INFO] finance_assistant attempt {attempt_count} - making tool calls")
        prompt = f"""You are an expert financial analyst.
Use get_finance_data and multiply_by_pi to answer: {user_question}"""
        response = model_with_tools.invoke([SystemMessage(prompt)] + state["messages"])

    return {
        "messages": [response],
        "attempt_count": attempt_count,
        "intermediate_results": {"last_successful_node": "finance_assistant"},
    }


def data_preprocessor(state: State):
    """Always succeeds — its write becomes a pending write if a peer node fails."""
    print("[SUCCESS] data_preprocessor completed")
    return {
        "intermediate_results": {
            **state.get("intermediate_results", {}),
            "preprocessed_data": {"status": "preprocessed", "timestamp": time.time()},
            "last_successful_node": "data_preprocessor",
        }
    }


def result_analyzer(state: State):
    """Fails exactly once to trigger LangGraph's pending-writes mechanism."""
    if not hasattr(result_analyzer, "_has_failed"):
        result_analyzer._has_failed = True
        print("[ERROR] result_analyzer simulated failure")
        raise Exception("Simulated analysis failure (first run)")

    print("[SUCCESS] result_analyzer completed")
    return {
        "intermediate_results": {
            **state.get("intermediate_results", {}),
            "analysis_results": {
                "status": "analyzed",
                "insights": ["Pattern A detected", "Trend B identified"],
                "timestamp": time.time(),
            },
            "last_successful_node": "result_analyzer",
        }
    }


def convergence_node(state: State):
    print("[INFO] Parallel processing completed, converging results")
    return {
        "intermediate_results": {
            **state.get("intermediate_results", {}),
            "last_successful_node": "convergence_node",
        }
    }


#  Graph (no checkpointer — injected by langgraph dev at serve time)
# ------------------------------------------------------------------

builder = StateGraph(State)

builder.add_node("finance_assistant", finance_assistant)
builder.add_node("tool_node", tool_node)
builder.add_node("data_preprocessor", data_preprocessor)
builder.add_node("result_analyzer", result_analyzer)
builder.add_node("convergence_node", convergence_node)

builder.add_edge(START, "finance_assistant")
builder.add_conditional_edges(
    "finance_assistant",
    should_continue,
    {"continue": "tool_node", "end": END},
)
builder.add_edge("tool_node", "data_preprocessor")
builder.add_edge("tool_node", "result_analyzer")
builder.add_edge("data_preprocessor", "convergence_node")
builder.add_edge("result_analyzer", "convergence_node")
builder.add_edge("convergence_node", "finance_assistant")

graph = builder.compile()


#  Standalone runner (injects its own SQLite checkpointer)
# ------------------------------------------------------------------

if __name__ == "__main__":
    import sqlite3
    import uuid
    from langgraph.checkpoint.sqlite import SqliteSaver

    def run():
        print("\n[DEMO] Fault-tolerance demonstration")
        print("=" * 60)

        if hasattr(result_analyzer, "_has_failed"):
            delattr(result_analyzer, "_has_failed")

        conn = sqlite3.connect("checkpoints.db", check_same_thread=False)
        saver = SqliteSaver(conn)
        saver.setup()
        g = builder.compile(checkpointer=saver)

        thread_id = f"demo-thread-{uuid.uuid4().hex[:8]}"
        cfg = {"configurable": {"thread_id": thread_id}}
        init_state = {
            "messages": [HumanMessage(content="Analyze the top 3 contracts by size and multiply the largest by π")],
            "attempt_count": 0,
            "finance_data": {},
            "intermediate_results": {},
        }

        for attempt in range(1, 4):
            print(f"\n[ATTEMPT {attempt}]")
            print("-" * 40)
            try:
                result = g.invoke(init_state if attempt == 1 else None, cfg)
                print("\n[SUCCESS] Completed")
                break
            except Exception as err:
                print(f"[FAILURE] {err}")
                state = g.get_state(cfg)
                print("[STATE] Intermediate results:", state.values.get("intermediate_results", {}))

    run()
