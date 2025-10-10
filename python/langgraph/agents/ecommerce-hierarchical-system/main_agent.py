from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.graph.message import AnyMessage, add_messages
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import ToolNode
from models import model
from billing_and_payments.supervisor import graph as billing_payments_graph
from order_management.supervisor import graph as order_management_graph
from promotions_and_loyalty.supervisor import graph as promotions_loyalty_graph
from prompts import (
    MAIN_SUPERVISOR_PROMPT,
    BILLING_PAYMENTS_SUPERVISOR_DESC,
    ORDER_MANAGEMENT_SUPERVISOR_DESC,
    PROMOTIONS_LOYALTY_SUPERVISOR_DESC,
)


@tool(description=BILLING_PAYMENTS_SUPERVISOR_DESC)
async def billing_and_payments_supervisor(query: str) -> str:
    """Route billing, payment, pricing, and refund inquiries to the Billing & Payments BU."""
    result = await billing_payments_graph.ainvoke(
        {"messages": [HumanMessage(content=query)]}
    )
    return result["messages"][-1].content


@tool(description=ORDER_MANAGEMENT_SUPERVISOR_DESC)
async def order_management_supervisor(query: str) -> str:
    """Route order and shipping inquiries to the Order Management BU."""
    result = await order_management_graph.ainvoke(
        {"messages": [HumanMessage(content=query)]}
    )
    return result["messages"][-1].content


@tool(description=PROMOTIONS_LOYALTY_SUPERVISOR_DESC)
async def promotions_and_loyalty_supervisor(query: str) -> str:
    """Route promotional code, discount, and loyalty program inquiries to the Promotions & Loyalty BU."""
    result = await promotions_loyalty_graph.ainvoke(
        {"messages": [HumanMessage(content=query)]}
    )
    return result["messages"][-1].content


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


# Bind tools to model
model_with_tools = model.bind_tools([
    billing_and_payments_supervisor,
    order_management_supervisor,
    promotions_and_loyalty_supervisor,
])

tools_node = ToolNode([
    billing_and_payments_supervisor,
    order_management_supervisor,
    promotions_and_loyalty_supervisor,
])


async def main_supervisor_node(state: State) -> dict:
    """Main supervisor that routes customer inquiries to appropriate BU supervisors."""
    result = await model_with_tools.ainvoke(
        [SystemMessage(content=MAIN_SUPERVISOR_PROMPT)] + state["messages"]
    )
    return {"messages": [result]}


def should_continue(state: State):
    """Determine if the supervisor needs to call more tools or end."""
    messages = state["messages"]
    last_message = messages[-1]
    if not last_message.tool_calls:
        return "end"
    else:
        return "continue"


# Build the main supervisor graph
builder = StateGraph(State)
builder.add_node("main_supervisor_node", main_supervisor_node)
builder.add_node("tools_node", tools_node)
builder.add_edge(START, "main_supervisor_node")
builder.add_conditional_edges(
    "main_supervisor_node",
    should_continue,
    {
        "continue": "tools_node",
        "end": END,
    },
)
builder.add_edge("tools_node", "main_supervisor_node")
graph = builder.compile()
