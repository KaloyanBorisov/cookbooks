# Trace Content Redaction with LangSmith

This project demonstrates how to redact sensitive content from LangSmith traces before they are sent to the LangSmith platform. The pattern is useful when your prompts contain confidential data — system prompts with proprietary instructions, PII, API keys embedded in messages, or any payload you do not want stored in your observability backend.

## How It Works

LangSmith's `Client` accepts two optional callbacks:

- `hide_inputs` — called with the raw inputs dict before they are logged
- `hide_outputs` — called with the raw outputs dict before they are logged

Both callbacks receive a dictionary and must return a dictionary. Whatever you return is what gets stored in the trace. You can redact specific fields, replace values with a placeholder, or return an empty dict to suppress the data entirely.

```
User code
    │
    ▼
openai_client.chat.completions.create(...)
    │
    ▼
LangSmith SDK intercepts the call
    │
    ├─► hide_inputs(inputs)  ──► redacted inputs  ──► stored in trace
    │
    └─► hide_outputs(outputs) ─► redacted outputs ──► stored in trace
```

The OpenAI client is wrapped with `wrap_openai`, which injects the tracing hook. The custom `langsmith_client` (with `hide_inputs` set) is passed per-call via `langsmith_extra={"client": langsmith_client}`.

## Project Structure

```
trace-content-redaction/
├── redact_system_prompt.ipynb   # Main walkthrough notebook
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

## Redaction Patterns

### Redact only system messages (used in the notebook)

```python
def redact_system_messages(inputs: dict) -> dict:
    messages = inputs.get("messages", [])
    redacted = [
        {"role": m.get("role"), "content": "REDACTED"}
        if m.get("role") == "system"
        else m
        for m in messages
    ]
    return {**inputs, "messages": redacted}
```

This preserves user and assistant messages in the trace, which is useful for debugging conversation flow while keeping your system prompt confidential.

### Redact all inputs and outputs

```python
langsmith_client = Client(
    hide_inputs=lambda inputs: {},
    hide_outputs=lambda outputs: {},
)
```

Use this when no part of the payload should be stored — for example in a production environment handling PII.

### Redact specific keys

```python
def redact_sensitive_keys(inputs: dict) -> dict:
    sensitive = {"api_key", "password", "ssn"}
    return {k: "REDACTED" if k in sensitive else v for k, v in inputs.items()}
```

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment variables

Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
```

| Variable | Description |
|---|---|
| `LANGSMITH_TRACING` | Set to `true` to enable tracing |
| `LANGSMITH_ENDPOINT` | LangSmith API endpoint (default: `https://api.smith.langchain.com`) |
| `LANGSMITH_API_KEY` | Your LangSmith API key |
| `LANGSMITH_PROJECT` | Project name traces will be grouped under |
| `OPENAI_API_KEY` | Your OpenAI API key |

### 3. Run the notebook

```bash
jupyter notebook redact_system_prompt.ipynb
```

## Key Code

```python
import openai
from langsmith import Client
from langsmith.wrappers import wrap_openai

# Wrap the OpenAI client to enable LangSmith tracing
openai_client = wrap_openai(openai.Client())

# Create a LangSmith client with a redaction function
langsmith_client = Client(
    hide_inputs=lambda inputs: redact_system_messages(inputs)
)

# Pass the custom client on a per-call basis
openai_client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you!"},
    ],
    langsmith_extra={"client": langsmith_client},
)
```

After this call, the LangSmith trace will show the system message content as `REDACTED` while all other messages remain intact.

## What Gets Redacted

The notebook redacts **system messages only** — specifically the `content` field of any message where `role == "system"`. Everything else is stored as-is.

Given this input:

```python
messages=[
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user",   "content": "Hello, how are you!"},
]
```

What LangSmith stores in the trace:

```python
messages=[
    {"role": "system", "content": "REDACTED"},          # ← redacted
    {"role": "user",   "content": "Hello, how are you!"},  # ← kept
]
```

The model response (output) is **not** redacted — it is stored in full. So in LangSmith you can see the user message and the assistant reply, but the system prompt is hidden.

This protects proprietary system prompt instructions from anyone with access to your LangSmith project, while preserving enough trace data to debug conversations.

## Running the Notebook in Docker

The Dockerfile runs a Jupyter server inside the container. Your project files are
volume-mounted from the host, so edits persist and no files are lost when the
container stops.

### Start the server

```bash
docker compose up
```

Jupyter starts on port 8888 with no token or password (safe for local use only).

### Connect VS Code to the container kernel

```
VS Code (local)
    │
    ├── Jupyter extension
    │       └─► http://localhost:8888
    │                   │
    │                   ▼
    │           Docker container
    │               ├── Python + deps
    │               ├── Jupyter server
    │               └── /app  ◄── mounted from your host
    │
    └── files stay on your machine
```

1. Open `redact_system_prompt.ipynb` in VS Code
2. Click **Select Kernel** (top right)
3. Choose **Existing Jupyter Server**
4. Enter `http://localhost:8888`

### Stop the server

```bash
docker compose down
```

### Notes

- VS Code itself runs locally — only the notebook kernel runs inside the container
- Terminal in VS Code still points to your local machine
- Env vars are loaded from `.env` via `docker-compose.yml`

## Reference

- [LangSmith docs — mask inputs and outputs](https://docs.smith.langchain.com/observability/how_to_guides/mask_inputs_outputs)
- [Sample trace with redacted system prompt](https://smith.langchain.com/public/7602d303-8f1a-41b3-beae-6fab07be3fa5/r)
