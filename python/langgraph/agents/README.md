# LangGraph Agents — Learning Progression

```
╔════════════════════════════════════════════════════════════════════════╗
║                    LANGGRAPH LEARNING PROGRESSION                      ║
╚════════════════════════════════════════════════════════════════════════╝

  ┌─────────────────────────────────────────────────────────────────┐
  │  1. basic-RAG                                          ★☆☆☆☆   │
  │─────────────────────────────────────────────────────────────────│
  │  Fixed pipeline. LLM only generates text.                       │
  │                                                                 │
  │  START → retrieve → grade → [rewrite?] → generate → END        │
  │                                                                 │
  │  Concepts: StateGraph, conditional edges, MemorySaver           │
  └──────────────────────────┬──────────────────────────────────────┘
                             │
                     adds tool calling
                     LLM drives the flow
                             │
                             ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │  2. agentic-RAG                                        ★★☆☆☆   │
  │─────────────────────────────────────────────────────────────────│
  │  LLM decides when and what to retrieve.                         │
  │                                                                 │
  │  START → agent ⇄ [retrieve_tool / web_search_tool] → END       │
  │                                                                 │
  │  Concepts: @tool, bind_tools, ReAct loop, ToolNode             │
  └──────────────────────────┬──────────────────────────────────────┘
                             │
                     adds parallel execution
                     multiple specialist subgraphs
                             │
                             ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │  3. arxiv-researcher                                   ★★★☆☆   │
  │─────────────────────────────────────────────────────────────────│
  │  Fan-out to parallel agents, fan-in to aggregate.               │
  │                                                                 │
  │                  ┌─ high_level_summary ─┐                       │
  │  download_paper ─┼─ detailed_summary   ─┼─ aggregate → END     │
  │                  └─ applications       ─┘                       │
  │                                                                 │
  │  Concepts: parallel edges, subgraphs, fan-out/fan-in           │
  └──────────────────────────┬──────────────────────────────────────┘
                             │
                     adds runtime configuration
                     deployable as an assistant
                             │
                             ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │  4. assistants-demo                                    ★★★★☆   │
  │─────────────────────────────────────────────────────────────────│
  │  Generic agent configured at runtime (model, tools, prompt).    │
  │                                                                 │
  │  config ──► create_react_agent(model, tools, prompt)           │
  │                        │                                        │
  │                   deployed via                                  │
  │               LangGraph Assistants API                          │
  │                                                                 │
  │  Concepts: runtime config, Assistants API, make_graph()        │
  └──────────────────────────┬──────────────────────────────────────┘
                             │
                     adds multi-agent hierarchy
                     agents routing to agents
                             │
                             ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │  5. ecommerce-hierarchical-system                      ★★★★★   │
  │─────────────────────────────────────────────────────────────────│
  │  Tree of supervisors. Each subgraph is itself a tool.           │
  │                                                                 │
  │                    ┌── billing supervisor                       │
  │  main supervisor ──┼── order supervisor                        │
  │                    └── promotions supervisor                    │
  │                              │                                  │
  │                      specialist agents                          │
  │                                                                 │
  │  Concepts: supervisor pattern, subgraph-as-tool, agent trees   │
  └─────────────────────────────────────────────────────────────────┘

  ───────────────────────────────────────────────────────────────────
  fixed graph  →  tool calling  →  parallel  →  config  →  hierarchy
  ───────────────────────────────────────────────────────────────────
```
