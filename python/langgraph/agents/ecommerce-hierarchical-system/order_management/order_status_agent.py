from langchain_core.messages import SystemMessage
from langgraph.graph.message import AnyMessage, add_messages
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import ToolNode
from .tools import get_order_details, cancel_order, update_shipping_address
from .prompts import ORDER_STATUS_PROMPT
from models import model

model_with_tools = model.bind_tools([get_order_details, cancel_order, update_shipping_address])


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


tools_node = ToolNode([get_order_details, cancel_order, update_shipping_address])


async def llm_node(state: State) -> dict:
    result = await model_with_tools.ainvoke(
        [SystemMessage(content=ORDER_STATUS_PROMPT)] + state["messages"]
    )
    return {"messages": [result]}


def should_continue(state: State):
    messages = state["messages"]
    last_message = messages[-1]
    if not last_message.tool_calls:
        return "end"
    else:
        return "continue"


builder = StateGraph(State)
builder.add_node("llm_node", llm_node)
builder.add_node("tools_node", tools_node)
builder.add_edge(START, "llm_node")
builder.add_conditional_edges(
    "llm_node",
    should_continue,
    {
        "continue": "tools_node",
        "end": END,
    },
)
builder.add_edge("tools_node", "llm_node")
graph = builder.compile()
