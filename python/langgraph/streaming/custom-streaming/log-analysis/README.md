> **LangGraph Feature Demonstrated:** Custom Streaming

# Custom Streaming Log Analysis

A streaming log analyzer that leverages the custom streaming mode in LangGraph and performs contextual error analysis on log files. The analyzer processes log data in chunks, scans for errors or warnings, and, if issues are detected, expands the analysis window to include surrounding context for deeper investigation.

## Features
- Processes log files in streaming fashion, chunk by chunk
- Scans each chunk for errors, warnings, or critical issues
- Automatically expands the context window for deeper analysis when issues are detected
- Provides detailed error analysis, root cause assessment, and recommended actions
- Outputs progress and analysis results to the console

## Usage

1. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the analyzer on a log file:
   ```bash
   python custom_streaming_log_analysis.py <log_file_path>
   ```
   Replace `<log_file_path>` with the path to your log file (e.g., `sample_log.log`).

## Files
- `custom_streaming_log_analysis.py`: Main script for streaming log analysis
- `sample_log.log`: Example log file for testing

## Requirements
See `requirements.txt` for the list of required Python packages.

---

## How It Works

### The Core Idea

The script scans a log file chunk by chunk. For each chunk it asks an LLM "any errors here?" — if no, it moves on cheaply. If yes, it pulls in the surrounding chunks for context and asks for a detailed root cause analysis. Progress events are emitted in real time throughout, so you see feedback as each chunk is processed rather than waiting for the whole file.

---

### Architecture: The Blackboard Pattern

This script is built around the **Blackboard pattern** — a classic AI architecture from the 1980s. The metaphor is a literal blackboard in a room:

- Multiple **experts** stand around the blackboard
- Each expert reads what is written, does their specialist work, and writes their result back
- A **controller** watches the blackboard and decides which expert should act next

In this script:

| Concept | Implementation |
|---|---|
| Blackboard | `State` TypedDict — shared by all nodes |
| Experts | `error_scan` and `deep_contextual_analysis` nodes |
| Controller | `route_after_scan` routing function + LangGraph runtime |

No node calls another node directly. They only read from and write to `State`. The controller reads `state["stage"]` to decide who runs next.

This is also a **Finite State Machine (FSM)**:

```
initial → error_scan → (no error) → complete → END
                     → (error)    → deep_analysis → complete → END
```

And a **dataflow graph** — execution is driven by data in state, not by explicit `if/else` control flow between functions.

---

### The Graph

```
START → error_scan ──(no error)──→ END
                   ──(error)────→ deep_analysis → END
```

**Node 1 — `error_scan` (cheap triage)**

Asks the LLM for a single binary answer: `ERROR_FOUND` or `NO_ISSUES`. This is intentionally cheap — most chunks in a healthy log file are clean, so you avoid paying for expensive analysis on every chunk.

- Reads: `state["chunk"]`
- Writes: `state["stage"]` (`"deep_analysis"` or `"complete"`)

**Node 2 — `deep_contextual_analysis` (expensive, conditional)**

Only runs when `error_scan` signals an error. Combines the current chunk with up to 2 surrounding chunks from the sliding buffer, then asks the LLM for a full root cause analysis, impact assessment, and recommended actions. Errors rarely appear in isolation — the cause is usually visible in earlier log lines.

- Reads: `state["chunk"]`, `state["context_chunks"]`
- Writes: `state["results"]`, `state["stage"]`

**Controller — `route_after_scan`**

Reads `state["stage"]` after `error_scan` completes and routes accordingly. It has no knowledge of what the nodes do — it only reads the blackboard.

```python
def route_after_scan(state: State):
    if state.get("stage") == "deep_analysis":
        return "deep_analysis"
    else:
        return END
```

---

### Custom Streaming: Real-Time Progress Events

Normally with an LLM call you wait for it to finish, then get the result. Custom streaming lets nodes push events **during** execution — before the LLM responds — so the caller sees live feedback.

**How it works:**

1. A node calls `writer = get_stream_writer()` — this returns a plain **synchronous** callable (no `await`)
2. The node calls `writer({"type": "progress", ...})` — this pushes an event into LangGraph's internal queue instantly
3. The `async for` loop in `process_file` receives these events as they arrive via `astream(stream_mode=["custom", "values"])`

The sending side is synchronous and instant. The receiving side is async. This separation means a node can report its own progress mid-execution without blocking.

**Two stream modes run simultaneously:**

| Mode | When delivered | What it contains |
|---|---|---|
| `custom` | As soon as `writer()` is called inside a node | Progress events, error signals, analysis results |
| `values` | After each node finishes | Full `State` snapshot — useful for debugging |

**Example event sequence for a chunk with an error:**

```
[CUSTOM]  {"type": "progress", "stage": "error_scan", "chunk": 3}   ← node starts
[CUSTOM]  {"type": "error_detected", "chunk": 3}                    ← LLM returned ERROR_FOUND
[VALUES]  {stage: "deep_analysis", chunk: "...", ...}               ← error_scan node finished
[CUSTOM]  {"type": "progress", "stage": "deep_analysis", "chunk": 3} ← deep analysis starts
[CUSTOM]  {"type": "detailed_analysis", "content": "..."}           ← analysis complete
[VALUES]  {stage: "complete", results: ["..."], ...}                ← deep_analysis node finished
```

---

### The Sliding Context Buffer

```python
self.chunk_buffer = deque(maxlen=3)
```

A `deque` with `maxlen=3` acts as a sliding window over the log file. As each new chunk is processed, it is added to the buffer and the oldest chunk is automatically dropped.

When an error is detected in chunk N, the buffer already contains chunks N-2 and N-1. These are passed into the graph as `context_chunks`, giving the LLM the surrounding log lines to reason about what led up to the error.

The buffer is populated **before** the graph runs for each chunk, so the context is always ready if needed.

---

### Extending to Real-Time Log Analysis

This architecture maps directly to live log streaming. The only change needed is the input source:

- Replace `TextLoader` with a live reader (Kafka consumer, socket, `tail -f` via `asyncio`)
- Each incoming batch of log lines becomes a chunk fed into the same graph
- The sliding buffer, triage pattern, and custom streaming all work identically on a live stream
