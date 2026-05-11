# agent-patterns

_A curated collection of agent patterns, examples, and templates built with LangGraph, LangSmith, and the broader LLM ecosystem._

## Structure

```
python/
├── langgraph/
│   ├── agent-quickstart/       # Quickstart examples across frameworks
│   │   ├── A2A/                # Agent-to-agent communication
│   │   ├── agno/
│   │   ├── autogen/
│   │   ├── browser-use/
│   │   ├── crewai/
│   │   ├── google-adk/
│   │   ├── langchain/
│   │   ├── langchain-mcp-adapters/
│   │   ├── langgraph/
│   │   ├── langgraph-codeact/
│   │   ├── langgraph-platform/
│   │   ├── langgraph_swarm/
│   │   ├── langmem/
│   │   ├── model_context_protocol/
│   │   ├── openai-agents/
│   │   └── smolagents/
│   ├── agents/                 # Full agent implementations
│   │   ├── agentic-RAG/
│   │   ├── arxiv-researcher/
│   │   ├── assistants-demo/
│   │   ├── basic-RAG/
│   │   ├── corrective-rag/
│   │   └── ecommerce-hierarchical-system/
│   ├── mcp-agent-template/     # Containerized MCP agent (Playwright + Firecrawl)
│   ├── mcp-auth-demo/          # Per-user MCP auth with Supabase + LangGraph
│   ├── persistence/            # Fault-tolerant graph patterns
│   ├── react-mcp-chat/         # ReAct agent with MCP chat UI
│   └── streaming/              # Custom streaming examples
└── langsmith/
    ├── evaluation/
    ├── observability/
    └── prompt-engineering/
```

## License

[MIT](LICENSE)
