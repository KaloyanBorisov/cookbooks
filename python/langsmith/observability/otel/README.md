# Tracing AWS Bedrock with LangSmith

This project demonstrates four ways to send traces from AWS Bedrock model and agent invocations to LangSmith. Methods 1–3 cover single model calls; Method 4 covers Bedrock Agents.

## How Tracing Works

Every method ultimately delivers the same thing to LangSmith: a structured record of an LLM call with inputs, outputs, token counts, and timing. What differs is **who instruments the call** and **how much manual work you do**.

```
Your code
    │
    ▼
AWS Bedrock API call
    │
    ├── Method 1: LangChain wraps the call automatically
    ├── Method 2: @traceable wraps your function
    ├── Method 3: You create OTel spans manually
    └── Method 4: BedrockInstrumentor patches boto3 automatically
    │
    ▼
LangSmith (via SDK or OTLP endpoint)
```

## Part I — Tracing Single Model Invocations

### Method 1: LangChain Integration (Recommended)

**How it works:** Use `ChatBedrock` or `ChatBedrockConverse` from `langchain-aws`. LangChain has built-in LangSmith tracing — as long as `LANGSMITH_TRACING=true` and `LANGSMITH_API_KEY` are set in your environment, every invocation is automatically traced with no extra code.

```python
from langchain_aws import ChatBedrock

llm = ChatBedrock(
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION_NAME,
    model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0"
)

llm.invoke([("human", "I love programming.")])
```

**What gets traced automatically:**
- Input messages
- Output message and stop reason
- Model ID
- Token usage (input, output, total)
- Latency

**When to use:** Any time you are already using LangChain to invoke Bedrock. Zero extra setup beyond env vars.

**Limitation:** Requires LangChain as a dependency. If you call `boto3` directly, this method does not apply.

---

### Method 2: `@traceable` Decorator

**How it works:** Wrap your existing boto3 invocation function with the `@traceable` decorator from the `langsmith` SDK. LangSmith intercepts the function call, records inputs and outputs, and sends the trace. You optionally pass a `process_inputs` function to reshape the raw boto3 payload into a cleaner format before logging.

```python
from langsmith import traceable
import json

def process_inputs(inputs: dict) -> dict:
    try:
        parsed = json.loads(inputs.get("body", "{}"))
        return {"messages": parsed["messages"]}
    except Exception:
        return inputs

@traceable(run_type="llm", process_inputs=process_inputs)
def run_model(client, modelId, contentType, accept, body):
    response = client.invoke_model(
        modelId=modelId, contentType=contentType, accept=accept, body=body
    )
    return json.loads(response.get("body").read())
```

Then call it exactly as you would call boto3 directly:

```python
run_model(
    client=client,
    modelId="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    contentType="application/json",
    accept="application/json",
    body=json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1500,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    })
)
```

**What gets traced:**
- Whatever `process_inputs` returns (inputs)
- The full boto3 response dict (outputs)
- Latency

**When to use:** When you call Bedrock directly with boto3 and want minimal changes to your code — just add the decorator and optionally a `process_inputs` cleaner.

**Limitation:** Token counts and model metadata are not automatically extracted — they come through as raw response fields unless you parse them yourself.

---

### Method 3: OpenTelemetry (OTel) Manual Spans

**How it works:** Set up an OpenTelemetry `TracerProvider` with an OTLP exporter that points to LangSmith's OTel endpoint. Then wrap your boto3 call in a span and manually attach attributes that LangSmith understands — inputs, outputs, token counts, model ID. LangSmith reads these standard `gen_ai.*` attributes to render the trace correctly.

**Step 1 — Configure the OTel pipeline (once per session):**

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

otlp_exporter = OTLPSpanExporter(
    endpoint=LANGSMITH_OTEL_ENDPOINT,   # https://api.smith.langchain.com/otel/v1/traces
    headers={
        "x-api-key": LANGSMITH_API_KEY,
        "Langsmith-Project": LANGSMITH_PROJECT
    }
)

provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
trace.set_tracer_provider(provider)
```

**Step 2 — Wrap your boto3 call in a span:**

```python
tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("call_bedrock") as span:
    span.set_attribute("langsmith.span.kind", "LLM")

    # Log inputs
    for i, message in enumerate(messages):
        span.set_attribute(f"gen_ai.prompt.{i}.content", message["content"])
        span.set_attribute(f"gen_ai.prompt.{i}.role", message["role"])

    # Call Bedrock
    response = client.invoke_model(
        modelId="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        contentType="application/json",
        accept="application/json",
        body=json.dumps({...})
    )
    response_body = json.loads(response.get("body").read())

    # Log outputs and token usage
    span.set_attribute("gen_ai.request.model", response_body["model"])
    span.set_attribute("gen_ai.completion.0.content", response_body["content"][0]["text"])
    span.set_attribute("gen_ai.completion.0.role", response_body["role"])
    span.set_attribute("gen_ai.usage.input_tokens", response_body["usage"]["input_tokens"])
    span.set_attribute("gen_ai.usage.output_tokens", response_body["usage"]["output_tokens"])
    span.set_attribute("gen_ai.usage.total_tokens",
        response_body["usage"]["input_tokens"] + response_body["usage"]["output_tokens"])
```

**Key OTel attributes LangSmith reads:**

| Attribute | Description |
|---|---|
| `langsmith.span.kind` | Set to `"LLM"` to render as an LLM span |
| `gen_ai.prompt.{i}.role` | Role of the i-th input message |
| `gen_ai.prompt.{i}.content` | Content of the i-th input message |
| `gen_ai.request.model` | Model ID returned in the response |
| `gen_ai.completion.{i}.role` | Role of the i-th output message |
| `gen_ai.completion.{i}.content` | Content of the i-th output message |
| `gen_ai.usage.input_tokens` | Prompt token count |
| `gen_ai.usage.output_tokens` | Completion token count |
| `gen_ai.usage.total_tokens` | Total token count |

**When to use:** When you are not using LangChain and cannot add the `@traceable` decorator — for example in an existing codebase where the call site is deep in a library. You instrument at the infrastructure level without touching application code structure.

**Limitation:** Most verbose — you manually set every attribute. If you forget a field, it won't appear in the trace.

---

## Part II — Tracing AWS Bedrock Agents

### Method 4: OTel with `BedrockInstrumentor`

**How it works:** The `openinference-instrumentation-bedrock` library auto-patches boto3 at import time. Once `BedrockInstrumentor().instrument()` is called, every subsequent boto3 Bedrock call — including agent invocations — is automatically wrapped in an OTel span and exported to LangSmith. No manual span creation needed.

```
boto3 bedrock-agent-runtime client
    │
    ▼
BedrockInstrumentor patches the client
    │
    ▼
Every invoke_agent() call → OTel span → OTLP exporter → LangSmith
```

**Step 1 — Configure OTel pipeline with the instrumentor:**

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from openinference.instrumentation.bedrock import BedrockInstrumentor

otlp_exporter = OTLPSpanExporter(
    endpoint=LANGSMITH_OTEL_ENDPOINT,
    headers={
        "x-api-key": LANGSMITH_API_KEY,
        "Langsmith-Project": LANGSMITH_PROJECT
    }
)

provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
trace.set_tracer_provider(provider)

BedrockInstrumentor().instrument(tracer_provider=provider)
```

**Step 2 — Invoke your agent as normal:**

```python
import time
import boto3

runtime_client = boto3.client(
    "bedrock-agent-runtime",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION_NAME
)

timestamp = int(time.time())
response = runtime_client.invoke_agent(
    agentId="B4MKQNWGZX",
    agentAliasId="TSTALIASID",
    inputText="what's the time now in utc?",
    sessionId=f"default-session1-{timestamp}",
    enableTrace=True,
)

completion = ""
for event in response.get("completion"):
    if "chunk" in event:
        completion += event["chunk"]["bytes"].decode()
    elif "trace" in event:
        print(event["trace"])
print(completion)
```

**When to use:** Tracing Bedrock Agents, or any boto3 Bedrock call where you want zero instrumentation code at the call site.

**Important:** `TracerProvider` and `BedrockInstrumentor` cannot be re-initialized in the same kernel session. If you already ran Method 3 in the same session, restart the kernel before running Part II.

---

## Comparison

| | Method 1 (LangChain) | Method 2 (@traceable) | Method 3 (OTel manual) | Method 4 (Instrumentor) |
|---|---|---|---|---|
| Code changes at call site | None | Add decorator | Wrap in span | None |
| Requires LangChain | Yes | No | No | No |
| Requires boto3 | No | Yes | Yes | Yes |
| Token counts auto-extracted | Yes | No | Manual | Yes |
| Works with Bedrock Agents | No | No | No | Yes |
| Setup complexity | Low | Low | High | Medium |

## Project Structure

```
otel/
├── tracing_bedrock_agents_otel.ipynb   # Main walkthrough notebook
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── .gitignore
```

## Setup

### 1. Configure environment variables

Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
```

| Variable | Description |
|---|---|
| `LANGSMITH_TRACING` | Set to `true` to enable tracing |
| `LANGSMITH_ENDPOINT` | LangSmith API endpoint |
| `LANGSMITH_OTEL_ENDPOINT` | LangSmith OTel collector endpoint |
| `LANGSMITH_API_KEY` | Your LangSmith API key |
| `LANGSMITH_PROJECT` | Project name traces will be grouped under |
| `AWS_ACCESS_KEY_ID` | AWS access key with Bedrock permissions |
| `AWS_SECRET_ACCESS_KEY` | AWS secret access key |
| `AWS_REGION_NAME` | AWS region (e.g. `us-east-2`) |

### 2. Run the notebook in Docker

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

1. Open `tracing_bedrock_agents_otel.ipynb` in VS Code
2. Click **Select Kernel** → **Existing Jupyter Server**
3. Enter `http://localhost:8888`

### Stop the server

```bash
docker compose down
```

## Reference

- [LangSmith OTel docs](https://docs.smith.langchain.com/observability/how_to_guides/trace_with_opentelemetry)
- [openinference-instrumentation-bedrock](https://github.com/Arize-ai/openinference/tree/main/python/instrumentation/openinference-instrumentation-bedrock)
- [LangChain AWS Bedrock integration](https://python.langchain.com/docs/integrations/chat/bedrock/)
