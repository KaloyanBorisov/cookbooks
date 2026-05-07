# Implemented Agents

This project provides two LangGraph agents, each serving a different purpose.

*   **agent (`deepagent_mcp`):** Advanced MCP orchestrator that implements tool discovery, planning, and execution using the `deepagents` architecture. Entry point: `src/deepagent_mcp/agent.py:create_mcp_orchestrator`.

*   **simple_agent:** Workflow enhancement agent that transforms task descriptions and a list of integrations into detailed, step-by-step workflows. Entry point: `src/simple_agent/graph.py:graph`. See [simple_agent README](../../src/simple_agent/README.md) for usage details.