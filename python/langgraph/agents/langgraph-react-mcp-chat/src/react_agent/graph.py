from datetime import datetime, timezone
from typing import Dict, List

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph
from langgraph.prebuilt import create_react_agent

from react_agent import utils
from react_agent.configuration import Configuration
from react_agent.state import InputState, State
from react_agent.tools import TOOLS

memory = MemorySaver()


async def call_model(
    state: State, config: RunnableConfig
) -> Dict[str, List]:
    configuration = Configuration.from_runnable_config(config)

    system_message = configuration.system_prompt.format(
        system_time=datetime.now(tz=timezone.utc).isoformat()
    )

    mcp_tools_config = await utils.load_mcp_config_json(configuration.mcp_tools)
    mcp_tools = mcp_tools_config.get("mcpServers", {})

    mcp_tool_list = []
    for name, server_config in mcp_tools.items():
        try:
            client = MultiServerMCPClient({name: server_config})
            tools = await client.get_tools()
            print(f"[MCP] loaded {name}: {[t.name for t in tools]}", flush=True)
            mcp_tool_list += tools
        except Exception as e:
            print(f"[MCP] failed {name}: {e}", flush=True)
    print(f"[MCP] all tools: {[t.name for t in mcp_tool_list + TOOLS]}", flush=True)
    all_tools = mcp_tool_list + TOOLS

    model = ChatOpenAI(
        model="gpt-4o", temperature=0.0
    )
    agent = create_react_agent(model, all_tools, checkpointer=memory)

    messages = [SystemMessage(content=system_message), *state.messages]
    response = await agent.ainvoke({"messages": messages}, config)

    new_messages = response["messages"][len(messages):]
    return {"messages": new_messages}


builder = StateGraph(State, input_schema=InputState, context_schema=Configuration)
builder.add_node(call_model)
builder.add_edge("__start__", "call_model")

graph = builder.compile()
graph.name = "ReAct Agent"
