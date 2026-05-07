# Project Dependencies and Metadata

This document outlines the key dependencies and metadata for the `langgraph-mcp` project, primarily sourced from `pyproject.toml`.

## Project Information

- **Name:** `langgraph-mcp`
- **Version:** `1.0.0`
- **Description:** LangGraph Solution Template for MCP
- **Authors:** Heuris Labs <hello@heuris.co>
- **License:** MIT
- **Readme:** `README.md`

## Requirements

- **Python Version:** >=3.12

## Core Dependencies

- `asyncio`
- `langchain`
- `langchain-core`
- `langchain-openai`
- `langchain-anthropic>=0.3.15`
- `langchain-mcp-adapters`
- `langgraph`
- `langgraph-cli[inmem]>=0.3.1`
- `langgraph-checkpoint-postgres>=2.0.23`
- `mcp[cli]` (Model Context Protocol library)
- `openai`
- `python-dotenv`
- `pydantic>=2.6`
- `psycopg[binary,pool]>=3.2.9`
- `sse-starlette>=2.1.0,<2.2.0`
- `requests>=2.32.3`
- `httpx>=0.24.0`
- `rich>=13.0.0`
- `langsmith>=0.3.37`
- `msgpack>=1.1.1`
- `deepagents`

## Development Dependencies (`dev`)

- `debugpy`
- `mypy`
- `ruff`
- `langgraph-cli[inmem]`

## Test Dependencies (`test`)

- `pytest`
- `langgraph-sdk`
- `requests`

## Build System

- **Requires:** `setuptools`, `wheel`
- **Build Backend:** `setuptools.build_meta`
- **Packages:** `langgraph_mcp` (from `src/langgraph_mcp`), `deepagent_mcp` (from `src/deepagent_mcp`), `simple_agent` (from `src/simple_agent`)
