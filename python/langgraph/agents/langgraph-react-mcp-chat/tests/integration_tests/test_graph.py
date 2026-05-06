import pytest

from react_agent import graph


@pytest.mark.asyncio
async def test_react_agent_simple_passthrough() -> None:
    """Test that the agent responds to a basic greeting."""
    res = await graph.ainvoke(
        {"messages": [("user", "Hi, what can you help me with?")]},
        {
            "configurable": {
                "system_prompt": "You are a helpful AI assistant.",
                "mcp_tools": "mcp_config_sample.json",
            }
        },
    )

    last_message = res["messages"][-1]
    assert last_message.content
    assert isinstance(last_message.content, str)
    assert len(last_message.content) > 0
