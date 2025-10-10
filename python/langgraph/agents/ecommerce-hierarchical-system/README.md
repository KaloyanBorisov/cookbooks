# Ecommerce System

A simple multi-agent ecommerce system built with LangChain and LangGraph. A top-level supervisor routes customer queries to specialized business unit (BU) supervisors that focus on billing & payments, order management, and promotions & loyalty tasks.

## Project Structure
- `main_agent.py`: Main supervisor graph that orchestrates BU supervisors.
- `billing_and_payments/`, `order_management/`, `promotions_and_loyalty/`: BU supervisors and their tools.
- `prompts.py`: System prompts and tool descriptions used by the supervisors.
- `test_agent.ipynb`: Notebook you can use to experiment with the assistant end-to-end.

## Getting Started
1. Install dependencies:
   ```bash
   uv sync
   ```
   or use `pip install -e .` if you prefer standard tooling.
2. Create a `.env` file based on `.env.example` and set any API keys (for example `OPENAI_API_KEY`) and LangSmith settings.

## Usage
- From a Python shell or script, import `graph` from `main_agent.py` and call `await graph.ainvoke({"messages": [...]})` with your conversation history.
- Alternatively, open `test_agent.ipynb` to try the flow interactively.

## LangSmith Tracing
- `.env.example` enables LangSmith tracing by default (`LANGSMITH_TRACING="true"`).
- Set `LANGSMITH_API_KEY` with your workspace token and optionally adjust `LANGSMITH_PROJECT` (defaults to `ecommerce`) to group runs.
- Once configured, every invocation reported through LangSmith includes the full supervisor/tool call tree, which makes it easy to debug agent routing.
- See an example trace [here](https://smith.langchain.com/public/704635b2-8735-4d0d-890f-67c26a5aeae4/r)

## Notes
- LangGraph CLI support is included; run `langgraph dev` if you want to inspect the graph locally.
