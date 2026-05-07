# LangGraph Integration Details

This document details how LangGraph is configured and integrated into the project, based on the `langgraph.json` file.

## Configuration (`langgraph.json`)

```json
{
  "name": "LangGraph Solution Template for MCP",
  "version": "1.0.0",
  "python_version": "3.12",
  "dependencies": ["."],
  "graphs": {
    "agent": {
      "path": "./src/deepagent_mcp/agent.py:create_mcp_orchestrator",
      "description": "Advanced MCP orchestrator agent using deepagents architecture with MCP tool integration."
    },
    "simple_agent": {
      "path": "./src/simple_agent/graph.py:graph",
      "description": "Workflow Enhancement Agent that transforms task descriptions and integrations into structured workflows."
    }
  },
  "env": ".env"
}
```

## Key Aspects

*   **Name & Version:** Defines the LangGraph project name and version (distinct from the Python package version in `pyproject.toml`).
*   **Python Version:** Specifies the target Python version (`3.12`).
*   **Dependencies:** Indicates project dependencies relevant to LangGraph CLI deployment (`.` means the current project).
*   **Graphs:** This is the core mapping that defines the available LangGraph graphs and their entry points.
    *   `agent` — the main MCP orchestrator, entry point at `src/deepagent_mcp/agent.py:create_mcp_orchestrator`.
    *   `simple_agent` — the workflow enhancement agent, entry point at `src/simple_agent/graph.py:graph`.
    *   This allows the LangGraph CLI and API server to discover and serve these graphs.
*   **Environment:** Specifies the environment file (`.env`) to load for configuration variables. 