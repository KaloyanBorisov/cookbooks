"""Main agent implementation for the simple agent."""

import os
from typing import Dict, Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END

from simple_agent.config import Configuration
from simple_agent.state import State, InputState
from langgraph_mcp.utils import load_chat_model


async def generate_response(state: State, *, config: RunnableConfig) -> Dict[str, Any]:
    cfg = Configuration.from_runnable_config(config)

    prompt = ChatPromptTemplate.from_messages([
        ("system", cfg.instructions),
        ("placeholder", "{messages}")
    ])

    model = load_chat_model(cfg.model)
    formatted_prompt = await prompt.ainvoke({"messages": state["messages"]}, config)
    response = await model.ainvoke(formatted_prompt.messages, config)

    return {"messages": [response]}


builder = StateGraph(State, input=InputState, config_schema=Configuration)
builder.add_node("generate_response", generate_response)
builder.add_edge(START, "generate_response")
builder.add_edge("generate_response", END)

graph = builder.compile()

__all__ = ["graph", "generate_response"]
