from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.graph.message import AnyMessage, add_messages
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import ToolNode
from models import model
from .transaction_lookup_agent import graph as transaction_lookup_graph
from .pricing_verification_agent import graph as pricing_verification_graph
from .refund_processing_agent import graph as refund_processing_graph
from .prompts import (
    BILLING_SUPERVISOR_PROMPT,
    TRANSACTION_LOOKUP_TOOL_DESC,
    PRICING_VERIFICATION_TOOL_DESC,
    REFUND_PROCESSING_TOOL_DESC,
)


@tool(description=TRANSACTION_LOOKUP_TOOL_DESC)
async def transaction_lookup_agent(query: str) -> str:
    result = await transaction_lookup_graph.ainvoke(
        {"messages": [HumanMessage(content=query)]}
    )
    return result["messages"][-1].content


@tool(description=PRICING_VERIFICATION_TOOL_DESC)
async def pricing_verification_agent(query: str) -> str:
    result = await pricing_verification_graph.ainvoke(
        {"messages": [HumanMessage(content=query)]}
    )
    return result["messages"][-1].content


@tool(description=REFUND_PROCESSING_TOOL_DESC)
async def refund_processing_agent(query: str) -> str:
    result = await refund_processing_graph.ainvoke(
        {"messages": [HumanMessage(content=query)]}
    )
    return result["messages"][-1].content


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


# Bind tools to model
model_with_tools = model.bind_tools(
    [transaction_lookup_agent, pricing_verification_agent, refund_processing_agent]
)

tools_node = ToolNode(
    [transaction_lookup_agent, pricing_verification_agent, refund_processing_agent]
)


async def supervisor_node(state: State) -> dict:
    result = await model_with_tools.ainvoke(
        [SystemMessage(content=BILLING_SUPERVISOR_PROMPT)] + state["messages"]
    )
    return {"messages": [result]}


def should_continue(state: State):
    messages = state["messages"]
    last_message = messages[-1]
    if not last_message.tool_calls:
        return "end"
    else:
        return "continue"


# Build the supervisor graph
builder = StateGraph(State)
builder.add_node("supervisor_node", supervisor_node)
builder.add_node("tools_node", tools_node)
builder.add_edge(START, "supervisor_node")
builder.add_conditional_edges(
    "supervisor_node",
    should_continue,
    {
        "continue": "tools_node",
        "end": END,
    },
)
builder.add_edge("tools_node", "supervisor_node")
graph = builder.compile()
