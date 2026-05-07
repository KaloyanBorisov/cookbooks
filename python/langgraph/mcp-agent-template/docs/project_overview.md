# Project Overview

## Purpose

This project demonstrates building a universal assistant using LangGraph and the Model Context Protocol (MCP). It combines LangGraph's workflow orchestration capabilities with MCP's standardized interface for connecting AI models to external tools and data sources.

The core idea is to implement a multi-agent pattern where an assistant routes user requests to appropriate agents. These agents then interact with MCP servers to utilize their offered tools, prompts, and resources.

## Key Components

*   **LangGraph:** Used to define and execute the assistant's workflow as a graph. Nodes represent actions (like routing, calling agents, or interacting with MCP), and edges define the control flow.
*   **MCP:** Provides a standardized way for LangGraph agents to communicate with external services (MCP Servers) offering tools and data.
*   **deepagent_mcp:** The primary MCP orchestrator agent built on the `deepagents` library, with intelligent tool discovery and planning.
*   **simple_agent:** A lightweight workflow enhancement agent that transforms task descriptions into structured workflows.

## Directory Structure

-   `src/deepagent_mcp/`: Primary MCP orchestrator agent.
    -   `agent.py`: Graph entry point (`create_mcp_orchestrator`).
    -   `config.py`: Configuration management.
    -   `state.py`: State definitions.
    -   `prompts.py`: System prompts.
    -   `tools.py`: Tool definitions.
    -   `utils.py`: Utility functions.
-   `src/simple_agent/`: Workflow enhancement agent.
    -   `graph.py`: Graph entry point (`graph`).
    -   `agent.py`: Agent implementation.
    -   `config.py`: Configuration management.
    -   `state.py`: State definitions.
-   `src/langgraph_mcp/`: Shared utilities.
    -   `utils.py`: Common utility functions (e.g., loading models).
-   `pyproject.toml`: Project metadata and dependencies.
-   `langgraph.json`: LangGraph-specific configuration, including graph entry points.
-   `README.md`: General project description for human readers.
-   `docs/`: Directory containing detailed markdown documentation. 