import os
from typing import List
from dotenv import load_dotenv

from langgraph.graph import StateGraph, END
from langgraph.graph.message import MessagesState
from langgraph.config import get_config
from langchain_core.messages import SystemMessage, AIMessage
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import ToolNode

load_dotenv()


class AgentState(MessagesState):
    # Extends MessagesState with a tools field so MCP tools are carried
    # through the graph without being re-fetched on every node execution
    tools: List[Tool]


def _get_auth_user():
    # auth.py attaches the user identity to the request config after JWT validation.
    # get_config() retrieves the current run's config from LangGraph context.
    config = get_config()
    return config.get("configurable", {}).get("langgraph_auth_user")


async def get_mcp_tools_node(state: AgentState) -> AgentState:
    """Connect to the GitHub MCP server using the authenticated user's PAT.

    This is the first node in the graph. It runs once per invocation and
    loads all available GitHub MCP tools into state so subsequent nodes
    don't need to reconnect. If no token is present, the agent continues
    without tools rather than failing hard.
    """
    user = _get_auth_user()
    if not user:
        return {"tools": []}

    github_token = user.get("github_token")
    if not github_token:
        return {"tools": []}

    try:
        github_url = os.getenv("GITHUB_MCP_URL", "https://api.githubcopilot.com/mcp/")
        mcp_client = MultiServerMCPClient({
            "github": {
                "transport": "streamable_http",
                "url": github_url,
                # The user's PAT is sent here — the MCP server authorizes as that user
                "headers": {"Authorization": f"Bearer {github_token}"}
            }
        })
        tools = await mcp_client.get_tools()
        return {"tools": tools}
    except Exception:
        return {"tools": []}


async def agent_node(state: AgentState) -> AgentState:
    """Invoke GPT-4o with the MCP tools bound.

    On each iteration the LLM either produces a final answer or emits
    tool_calls. If tool_calls are present, should_continue() routes to
    the tools node; otherwise the graph ends.
    """
    user = _get_auth_user()
    user_email = user.get("email", "Unknown") if user else "Not authenticated"
    tools = state.get("tools", [])

    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    if tools:
        # bind_tools tells the LLM what tools are available and how to call them
        llm = llm.bind_tools(tools)

    system_message = SystemMessage(content=f"""You are a helpful GitHub assistant with access to GitHub tools via MCP.
User: {user_email}
Available tools: {len(tools)}""")

    response = await llm.ainvoke([system_message] + state["messages"])
    return {"messages": state["messages"] + [response]}


def should_continue(state: AgentState) -> str:
    """Route to the tools node if the LLM requested tool calls, otherwise end."""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END


async def tool_node(state: AgentState) -> AgentState:
    """Execute the tool calls requested by the LLM.

    Uses the MCP tools already loaded into state — no reconnection needed.
    After execution, the graph loops back to agent_node so the LLM can
    reason over the tool results and decide what to do next.
    """
    tools = state.get("tools", [])
    if not tools:
        return {"messages": state["messages"] + [AIMessage(content="No tools available.")]}
    return await ToolNode(tools).ainvoke(state)


def create_graph() -> StateGraph:
    """Build and compile the LangGraph graph.

    Flow:
        get_mcp_tools  →  agent  →  (tools  →  agent)*  →  END
    """
    graph = StateGraph(AgentState)
    graph.add_node("get_mcp_tools", get_mcp_tools_node)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("get_mcp_tools")
    graph.add_edge("get_mcp_tools", "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    # After tool execution, loop back to the agent so it can process results
    graph.add_edge("tools", "agent")
    return graph.compile()


graph = create_graph()
