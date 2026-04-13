# Simple RAG Agent

A basic, stateless RAG agent built with LangGraph and leveraging Chroma's open-source vector database.

## Overview

This agent answers questions about LangGraph by retrieving relevant documentation chunks from a local vector database and passing them as context to an LLM.

## Project Structure

```
basic-RAG/
├── agent.py          # LangGraph graph definition and entry point
├── utils.py          # Vectorstore setup, LLM, and retriever
├── requirements.txt  # Python dependencies
└── .env              # API keys (not committed)
```

## How it works

### `agent.py`

**1. Startup**

When the file loads it does 3 things in order:
- Loads `.env` so API keys are available
- Registers Phoenix tracing — from this point every LangChain/LangGraph call is automatically recorded
- Calls `get_langgraph_docs_retriever()` from `utils.py` — loads the vectorstore from disk (or builds it on first run)

**2. State**

The graph passes a state dict between nodes — shared memory for the current run:

```
GraphState
├── question   → the user's input question
├── documents  → chunks retrieved from the vectorstore
└── generation → the LLM's final answer
```

`InputState` restricts what the caller needs to provide — just `question`. The other fields get filled in as the graph runs.

**3. Node 1 — `retrieve_documents`**

- Reads `question` from state
- Calls `retriever.invoke(question)` — embeds the question and finds the most similar chunks in Chroma
- Returns `{"documents": [...]}` which gets merged into the state

**4. RAG Prompt**

A template with two placeholders — `{question}` and `{context}` (the retrieved chunks joined together). This is what gets sent to the LLM.

**5. Node 2 — `generate_response`**

- Reads `question` and `documents` from state
- Joins all document chunks into one string
- Fills the RAG prompt template
- Calls `llm.invoke()` with the formatted prompt
- Returns `{"generation": <LLM response>}` into state

**6. Graph wiring**

```
START → retrieve_documents → generate_response → END
```

Linear flow — no branches, no loops. Each edge passes the full state to the next node.

**7. Entry point**

Only runs when executed directly (`python agent.py`). Invokes the compiled graph with a question and prints the answer from `result["generation"].content`.

### `utils.py`

Contains all setup logic and one function:

**Module-level setup (runs on import)**

- `DB_PATH` — absolute path to the vectorstore folder, always resolved relative to `utils.py` regardless of where you run the script from
- `llm` — a `gpt-4o` client with `temperature=0` (deterministic answers)
- `embedding_model` — OpenAI embeddings client (`text-embedding-ada-002`) used to convert text into vectors
- `LANGGRAPH_DOCS` — list of 10 LangGraph documentation URLs that form the knowledge base

**`get_langgraph_docs_retriever()`**

Has two execution paths:

- **Fast path (DB exists):** Loads Chroma from disk, verifies it has embeddings, and returns the retriever immediately with no API calls
- **Slow path (first run):** Fetches each URL via `WebBaseLoader`, splits content into 200-token chunks with `RecursiveCharacterTextSplitter`, embeds each chunk via OpenAI, persists to disk, then returns the retriever

If the DB exists but is empty (e.g. a previous run crashed mid-way), it automatically deletes the broken DB and rebuilds.

`as_retriever(lambda_mult=0)` returns a retriever that finds the most similar chunks by pure cosine similarity when given a question.

### Vectorstore (Chroma)

Chroma uses two storage mechanisms:

- `chroma.sqlite3` — stores document text, metadata, and collection info
- `*.bin` files — binary HNSW index for fast vector similarity search

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file:
```
OPENAI_API_KEY=sk-...
PHOENIX_API_KEY=...
PHOENIX_COLLECTOR_ENDPOINT=https://app.phoenix.arize.com/...
```

3. Run the agent:
```bash
python agent.py
```

On first run the vectorstore will be built by scraping the documentation URLs — this requires OpenAI API calls for embeddings. Subsequent runs load from disk instantly.

## Observability

Phoenix tracing is enabled via `arize-phoenix-otel` and `openinference-instrumentation-langchain`. All LLM calls, retrievals, and graph steps are automatically traced and visible in your Phoenix dashboard.
