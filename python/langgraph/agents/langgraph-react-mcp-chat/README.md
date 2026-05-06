# LangGraph ReAct MCP Chat

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![LangChain](https://img.shields.io/badge/LangChain-0.3.23+-green.svg)
![LangGraph](https://img.shields.io/badge/LangGraph-0.3.25+-orange.svg)

A LangGraph-based ReAct agent that connects to any [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server at runtime. Tools are loaded dynamically from a JSON config file — no code changes needed to add or swap MCP servers.

## Features

- **Dynamic MCP tool loading** — add or swap MCP servers via `mcp_config.json` without touching code
- **Built-in Tavily web search** — always available alongside MCP tools
- **Conversation memory** — thread-based history via LangGraph `MemorySaver`
- **Docker-first** — run with `docker compose up --build`, no local Node/Python setup required
- **LangGraph Studio compatible** — interact via Studio UI at `http://localhost:2024`

## Architecture

```mermaid
flowchart TD
    User([User]) -->|message| Studio[LangGraph Studio\nlocalhost:2024]
    Studio --> OuterGraph

    subgraph OuterGraph["Outer StateGraph"]
        direction TB
        START([__start__]) --> call_model
        call_model --> END([__end__])
    end

    subgraph call_model["call_model node"]
        direction TB
        Config[Load Configuration\nsystem_prompt · mcp_tools path] --> LoadMCP
        LoadMCP[Load mcp_config.json] --> PerServer

        subgraph PerServer["Per-server loop (isolated try/except)"]
            direction LR
            Brave[brave-search\nbrave_web_search\nbrave_local_search]
            Hyper[hyperbrowser\nscrape · crawl\nextract · browser_use]
        end

        PerServer --> Merge[Merge MCP tools + Tavily]
        Merge --> ReAct

        subgraph ReAct["Inner ReAct Agent (create_react_agent)"]
            direction TB
            GPT[GPT-4o] -->|tool_call| Tools[MCP Tools + Tavily]
            Tools -->|tool_result| GPT
            GPT -->|final answer| Reply[AIMessage]
        end
    end

    subgraph Docker["Docker Container"]
        OuterGraph
        Brave
        Hyper
    end

    subgraph MCPServers["MCP Subprocesses (stdio)"]
        BraveProc[mcp-server-brave-search]
        HyperProc[hyperbrowser-mcp]
    end

    Brave <-->|stdio| BraveProc
    Hyper <-->|stdio| HyperProc

    BraveProc -->|BRAVE_API_KEY| BraveAPI[Brave Search API]
    HyperProc -->|HYPERBROWSER_API_KEY| HyperAPI[Hyperbrowser Cloud]
```

### Key design decisions

- **Two-layer graph** — the outer `StateGraph` is minimal (single node), keeping the graph structure simple while the inner `create_react_agent` handles the full tool-call loop.
- **Per-server MCP isolation** — each MCP server is loaded in its own `try/except`. One failing server does not drop the others.
- **stdio transport** — MCP servers run as subprocesses inside the container. All secrets stay in `.env` and are inherited by subprocesses automatically — nothing hardcoded in `mcp_config.json`.
- **Volume-mounted `src/`** — code changes are picked up by LangGraph's file watcher without a rebuild.

## Setup

### Docker (recommended)

**1. Configure environment variables**

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_openai_api_key
TAVILY_API_KEY=your_tavily_api_key
BRAVE_API_KEY=your_brave_api_key
HYPERBROWSER_API_KEY=your_hyperbrowser_api_key
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_PROJECT=your_langsmith_project
```

**2. Build and run**

```bash
docker compose up --build
```

Open LangGraph Studio at `http://localhost:2024`.

### Local (without Docker)

```bash
pip install -r requirements.txt
langgraph dev
```

## MCP Configuration

MCP servers are defined in `src/react_agent/mcp_config.json`. Each entry is launched as a stdio subprocess inside the container:

```json
{
    "mcpServers": {
        "brave-search": {
            "transport": "stdio",
            "command": "mcp-server-brave-search",
            "args": []
        },
        "hyperbrowser": {
            "transport": "stdio",
            "command": "hyperbrowser-mcp",
            "args": []
        }
    }
}
```

All API keys are read from `.env` — do not hardcode secrets in `mcp_config.json`.

To add a new MCP server:
1. Add its npm package to the `Dockerfile` `npm install -g` line
2. Add its entry to `mcp_config.json`
3. Rebuild with `docker compose up --build`

## Project Structure

```
.
├── Dockerfile
├── docker-compose.yml
├── langgraph.json
├── pyproject.toml
├── requirements.txt
└── src/
    └── react_agent/
        ├── graph.py          # Outer StateGraph + call_model node
        ├── configuration.py  # Configurable fields (system_prompt, mcp_tools)
        ├── state.py          # State / InputState definitions
        ├── tools.py          # Built-in tools (Tavily)
        ├── prompts.py        # System prompt template
        ├── utils.py          # mcp_config.json loader
        └── mcp_config.json   # MCP server definitions
```

## License

Apache License 2.0 — see [LICENSE](LICENSE).
