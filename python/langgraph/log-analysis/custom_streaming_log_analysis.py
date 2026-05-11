import asyncio
import base64
import re
import sys
from typing import TypedDict, List, Optional, Annotated
from collections import deque

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, AIMessage, AnyMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.config import get_stream_writer
from dotenv import load_dotenv

load_dotenv()


# --- OUTER GRAPH STATE ---
# messages: chat history (enables Studio chat UI)
# file_path: log file path, set once in the Studio "Input" panel before running
class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    file_path: Optional[str]


# --- INNER GRAPH STATE (BLACKBOARD) ---
# Shared state for the analysis sub-graph. All nodes read/write here.
#
# Fields:
#   chunk         - the current log text being analyzed
#   chunk_index   - which chunk number we're on (for progress reporting)
#   results       - accumulated analysis results across nodes
#   stage         - routing signal: "initial" → "deep_analysis" or "complete"
#   context_chunks - surrounding chunks passed in when an error is found
class State(TypedDict):
    chunk: str
    chunk_index: int
    results: List[str]
    stage: str
    context_chunks: Optional[List[str]]


class ContextualAnalyzer:
    def __init__(self):
        self.llm = init_chat_model(model="openai:gpt-4o-mini")
        self.graph = self._build_graph()

        # Sliding window buffer — keeps the last 3 processed chunks in memory.
        # When an error is detected in chunk N, we pass chunks N-2 and N-1
        # as context so the LLM can reason about what led to the error.
        self.chunk_buffer = deque(maxlen=3)

    def _build_graph(self):

        # --- NODE 1: error_scan (cheap triage) ---
        # Fast binary decision: error or no error.
        # BLACKBOARD PATTERN: reads state["chunk"], writes state["stage"].
        # CUSTOM STREAMING: writer() pushes events mid-execution without await.
        async def error_scan(state: State, config):
            writer = get_stream_writer()

            writer({"type": "progress", "chunk": state["chunk_index"], "stage": "error_scan"})

            response = await self.llm.ainvoke(
                [
                    {
                        "role": "system",
                        "content": "Scan this log chunk for errors, warnings, or critical issues. Respond with 'ERROR_FOUND' if issues detected, otherwise 'NO_ISSUES'.",
                    },
                    {"role": "user", "content": state["chunk"]},
                ],
                config,
            )

            has_error = "ERROR_FOUND" in response.content.upper()

            if has_error:
                writer({"type": "error_detected", "chunk": state["chunk_index"]})
                return {"stage": "deep_analysis", "results": state["results"]}
            else:
                writer({"type": "clean_chunk", "chunk": state["chunk_index"]})
                return {"stage": "complete", "results": state["results"] + ["No issues found"]}

        # --- NODE 2: deep_contextual_analysis (expensive expert) ---
        # Only runs when error_scan sets stage="deep_analysis".
        # Uses surrounding chunks from the sliding buffer for broader context.
        async def deep_contextual_analysis(state: State, config):
            writer = get_stream_writer()

            writer({"type": "progress", "chunk": state["chunk_index"], "stage": "deep_analysis"})

            if state.get("context_chunks"):
                combined_context = "\n".join(
                    [f"CHUNK {i+1}:\n{chunk}" for i, chunk in enumerate(state["context_chunks"])]
                )
                context_info = f"Analyzing error with expanded context ({len(state['context_chunks'])} chunks)"
            else:
                combined_context = state["chunk"]
                context_info = "Analyzing error (no additional context available)"

            response = await self.llm.ainvoke(
                [
                    {
                        "role": "system",
                        "content": f"""You are analyzing log data with expanded context. {context_info}.

                    Provide detailed analysis of:
                    1. What errors/issues are present
                    2. Root cause analysis using the surrounding context
                    3. Impact assessment
                    4. Recommended actions

                    Focus on how the context chunks help understand the issue better.""",
                    },
                    {"role": "user", "content": combined_context},
                ],
                config,
            )

            writer({"type": "detailed_analysis", "content": response.content})
            return {"stage": "complete", "results": state["results"] + [response.content]}

        workflow = StateGraph(State)
        workflow.add_node("error_scan", error_scan)
        workflow.add_node("deep_analysis", deep_contextual_analysis)
        workflow.add_edge(START, "error_scan")

        def route_after_scan(state: State):
            return "deep_analysis" if state.get("stage") == "deep_analysis" else END

        workflow.add_conditional_edges(
            "error_scan", route_after_scan, {"deep_analysis": "deep_analysis", END: END}
        )
        workflow.add_edge("deep_analysis", END)

        return workflow.compile()

    def _get_context_chunks(self, current_index: int) -> List[str]:
        buffer_list = list(self.chunk_buffer)
        if len(buffer_list) == 3:
            return buffer_list
        if len(buffer_list) >= 2:
            return buffer_list[-2:]
        return []

    async def process_text(self, text: str, label: str = "input") -> str:
        print(f"\n{'='*60}")
        print(f"  LOG ANALYSIS: {label}")
        print(f"{'='*60}\n")

        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        chunks = splitter.split_text(text)
        chunk_index = 0
        findings = []

        for chunk_content in chunks:
            chunk_index += 1
            self.chunk_buffer.append(chunk_content)
            context_chunks = self._get_context_chunks(chunk_index)

            async for stream_data in self.graph.astream(
                {
                    "chunk": chunk_content,
                    "chunk_index": chunk_index,
                    "results": [],
                    "stage": "initial",
                    "context_chunks": context_chunks if len(context_chunks) > 1 else None,
                },
                stream_mode=["custom", "values"],
            ):
                mode, data = stream_data

                if mode == "custom":
                    if data.get("type") == "progress":
                        stage = data.get("stage", "unknown")
                        if stage == "error_scan":
                            print(f"  [ Chunk {data['chunk']:>3} ]  scanning...", end="\r")
                        elif stage == "deep_analysis":
                            print(f"  [ Chunk {data['chunk']:>3} ]  running deep analysis...")
                    elif data.get("type") == "error_detected":
                        print(f"  [ Chunk {data['chunk']:>3} ]  !! ERROR DETECTED — escalating to deep analysis")
                    elif data.get("type") == "clean_chunk":
                        print(f"  [ Chunk {data['chunk']:>3} ]  OK")
                    elif data.get("type") == "detailed_analysis":
                        findings.append((chunk_index, data["content"]))

        print(f"\n{'='*60}")
        if findings:
            print(f"  DEEP ANALYSIS RESULTS  ({len(findings)} issue(s) found)")
            print(f"{'='*60}")
            for idx, (chunk_num, content) in enumerate(findings, 1):
                print(f"\n  Finding #{idx}  (chunk {chunk_num})")
                print(f"  {'-'*56}")
                for line in content.strip().splitlines():
                    print(f"  {line}")
                print()
        else:
            print("  RESULT: No issues detected across all chunks.")
        print(f"{'='*60}\n")

        if findings:
            summary = f"Found {len(findings)} issue(s):\n\n"
            summary += "\n\n---\n\n".join(content for _, content in findings)
        else:
            summary = f"No issues detected across {chunk_index} chunks."

        return summary

    async def process_file(self, file_path: str) -> str:
        with open(file_path, "r", errors="replace") as f:
            text = f.read()
        return await self.process_text(text, label=file_path)


# --- OUTER GRAPH (Studio UI entry point) ---
# Accepts either:
#   - A plain text message containing a file path  (/app/sample_log.log)
#   - A multipart message with a file attachment from Studio's "Upload files" button

_analyzer = ContextualAnalyzer()


def _extract_file_content(message: HumanMessage) -> tuple[str | None, str]:
    """Return (raw_text, label) from a HumanMessage, handling Studio file attachments."""
    content = message.content

    if isinstance(content, str):
        return None, content.strip()  # plain path

    # Multipart content blocks sent by Studio when a file is attached
    for block in content:
        if not isinstance(block, dict):
            continue
        block_type = block.get("type")

        if block_type == "file":
            file_info = block.get("file", {})
            filename = file_info.get("filename", "uploaded_file")
            source_type = file_info.get("source_type", "")
            if source_type == "base64":
                raw = base64.b64decode(file_info["data"]).decode("utf-8", errors="replace")
                return raw, filename
            if source_type == "text":
                return file_info.get("data", ""), filename

        # Fallback: inline document block (older Studio versions)
        if block_type == "document":
            source = block.get("source", {})
            if source.get("type") == "base64":
                raw = base64.b64decode(source["data"]).decode("utf-8", errors="replace")
                return raw, "uploaded_file"
            if source.get("type") == "text":
                return source.get("data", ""), "uploaded_file"

    # No file block found — collect plain text parts and treat as a file path
    text_parts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
    return None, " ".join(text_parts).strip()


async def analyze_log(state: AgentState):
    file_path = state.get("file_path") or ""

    # Fall back to extracting a path from the last human message
    if not file_path:
        last_message = next(
            (m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), None
        )
        if last_message:
            content = last_message.content
            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                text = " ".join(
                    b.get("text", "") for b in content
                    if isinstance(b, dict) and b.get("type") == "text"
                )
            else:
                text = ""
            match = re.search(r"(/\S+)", text)
            if match:
                file_path = match.group(1)

    if not file_path:
        return {"messages": [AIMessage(content="Please include the file path in your message (e.g. `/app/sample_log.log`) or set the **file_path** field in the Studio input panel.")]}

    try:
        result = await _analyzer.process_file(file_path)
    except FileNotFoundError:
        result = f"File not found: {file_path}\n\nPlace your log file in the project directory and use path /app/<filename>.log"
    except Exception as e:
        result = f"Error processing file: {e}"

    return {"messages": [AIMessage(content=result)]}


builder = StateGraph(AgentState)
builder.add_node("analyze_log", analyze_log)
builder.add_edge(START, "analyze_log")
builder.add_edge("analyze_log", END)

graph = builder.compile()


# --- CLI entry point ---
async def main():
    if len(sys.argv) != 2:
        print("Usage: python custom_streaming_log_analysis.py <log_file_path>")
        sys.exit(1)

    result = await graph.ainvoke({
        "messages": [HumanMessage(content=sys.argv[1])]
    })
    print(result["messages"][-1].content)


if __name__ == "__main__":
    asyncio.run(main())
