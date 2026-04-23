import asyncio
import sys
from typing import TypedDict, List, Optional
from collections import deque

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END
from langgraph.config import get_stream_writer
from dotenv import load_dotenv

load_dotenv()


# --- BLACKBOARD (Shared State) ---
# This TypedDict is the "blackboard" in the Blackboard pattern.
# All nodes (experts) read from and write to this shared structure.
# No node calls another node directly — they only communicate through State.
#
# Fields:
#   chunk         - the current log text being analyzed
#   chunk_index   - which chunk number we're on (for progress reporting)
#   results       - accumulated analysis results across nodes
#   stage         - the key signal the controller reads to decide routing:
#                   "initial" → "deep_analysis" or "complete"
#   context_chunks - surrounding chunks passed in when an error is found,
#                   so the LLM understands what happened before the error
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
        # maxlen=3 means older chunks are automatically dropped as new ones arrive.
        self.chunk_buffer = deque(maxlen=3)

    def _build_graph(self):

        # --- NODE 1: error_scan (the cheap triage expert) ---
        # This node's only job is a fast binary decision: error or no error.
        # It asks the LLM for a single-word answer to avoid paying the cost
        # of deep analysis on every chunk. Most chunks in healthy logs are clean.
        #
        # BLACKBOARD PATTERN: reads state["chunk"], writes state["stage"].
        # The controller (route_after_scan) will read stage to decide next step.
        #
        # CUSTOM STREAMING: get_stream_writer() returns a plain synchronous callable.
        # Calling writer({...}) pushes an event into LangGraph's internal queue instantly,
        # with no await needed. The async for loop in process_file receives these events
        # as they are pushed — this is how real-time progress is achieved mid-execution.
        async def error_scan(state: State, config):
            writer = get_stream_writer()

            # Push a progress event immediately when this node starts —
            # the caller sees this before the LLM call even begins.
            writer(
                {
                    "type": "progress",
                    "chunk": state["chunk_index"],
                    "stage": "error_scan",
                }
            )

            # Cheap LLM call: binary classification only.
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
                # Signal the controller to route to deep_analysis next.
                # The node writes the decision into state; it does NOT call deep_analysis itself.
                writer({"type": "error_detected", "chunk": state["chunk_index"]})
                return {"stage": "deep_analysis", "results": state["results"]}
            else:
                # Signal the controller that we are done — route to END.
                writer({"type": "clean_chunk", "chunk": state["chunk_index"]})
                return {
                    "stage": "complete",
                    "results": state["results"] + ["No issues found"],
                }

        # --- NODE 2: deep_contextual_analysis (the expensive expert) ---
        # Only runs when error_scan wrote stage="deep_analysis" into state.
        # Uses surrounding chunks (from the sliding buffer) to give the LLM
        # broader context — errors rarely appear in isolation, the cause is
        # usually visible in earlier log lines.
        #
        # BLACKBOARD PATTERN: reads state["chunk"] and state["context_chunks"],
        # writes state["results"] and state["stage"].
        async def deep_contextual_analysis(state: State, config):
            writer = get_stream_writer()

            # Real-time event: caller knows deep analysis is starting right now.
            writer(
                {
                    "type": "progress",
                    "chunk": state["chunk_index"],
                    "stage": "deep_analysis",
                }
            )

            # If we have surrounding chunks, combine them so the LLM sees
            # the full picture of what happened before the error.
            if state.get("context_chunks"):
                combined_context = "\n".join(
                    [
                        f"CHUNK {i+1}:\n{chunk}"
                        for i, chunk in enumerate(state["context_chunks"])
                    ]
                )
                context_info = f"Analyzing error with expanded context ({len(state['context_chunks'])} chunks)"
            else:
                combined_context = state["chunk"]
                context_info = "Analyzing error (no additional context available)"

            # Expensive LLM call: full root cause analysis with context.
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

            # Push the full analysis as a custom stream event so the caller
            # receives it immediately, before this node's return value is processed.
            writer({"type": "detailed_analysis", "content": response.content})
            return {
                "stage": "complete",
                "results": state["results"] + [response.content],
            }

        # --- GRAPH ASSEMBLY ---
        # Nodes are registered but not wired to call each other.
        # The graph runtime (controller) handles execution order.
        workflow = StateGraph(State)
        workflow.add_node("error_scan", error_scan)
        workflow.add_node("deep_analysis", deep_contextual_analysis)

        # Every chunk always starts at error_scan — the cheap triage step.
        workflow.add_edge(START, "error_scan")

        # --- CONTROLLER (routing function) ---
        # This is the controller in the Blackboard pattern.
        # It reads the blackboard (state) and decides which expert runs next.
        # It has no knowledge of what the nodes do — it only reads state["stage"].
        #
        # This is also the Finite State Machine transition:
        #   stage == "deep_analysis"  →  run deep_analysis node
        #   anything else             →  we are done, go to END
        def route_after_scan(state: State):
            stage = state.get("stage", "complete")
            if stage == "deep_analysis":
                return "deep_analysis"
            else:
                return END

        workflow.add_conditional_edges(
            "error_scan", route_after_scan, {"deep_analysis": "deep_analysis", END: END}
        )
        workflow.add_edge("deep_analysis", END)

        return workflow.compile()

    def _get_context_chunks(self, current_index: int) -> List[str]:
        # Returns up to 3 recent chunks from the sliding buffer.
        # These are passed into state so deep_analysis has surrounding context.
        # The buffer already holds them — we just read what's there.
        context_chunks = []
        buffer_list = list(self.chunk_buffer)

        if len(buffer_list) >= 2:
            context_chunks = buffer_list[-2:]
        if len(buffer_list) == 3:
            context_chunks = buffer_list

        return context_chunks

    async def process_file(self, file_path: str):
        print(f"\n{'='*60}")
        print(f"  LOG ANALYSIS: {file_path}")
        print(f"{'='*60}\n")

        loader = TextLoader(file_path)
        # Split the file into ~1000 char chunks with 100 char overlap so
        # errors near chunk boundaries aren't missed due to truncation.
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        chunk_index = 0
        findings = []

        for document in loader.lazy_load():
            for chunk in splitter.split_documents([document]):
                chunk_index += 1
                chunk_content = chunk.page_content

                # Add this chunk to the sliding buffer BEFORE running the graph,
                # so that if an error is found, the buffer already contains it
                # along with up to 2 preceding chunks for context.
                self.chunk_buffer.append(chunk_content)
                context_chunks = self._get_context_chunks(chunk_index)

                # stream_mode=["custom", "values"] means we receive two kinds of events:
                #   "custom" — events pushed by nodes via get_stream_writer() mid-execution
                #   "values" — full state snapshots after each node completes
                # Each iteration yields a (mode, data) tuple.
                async for stream_data in self.graph.astream(
                    {
                        "chunk": chunk_content,
                        "chunk_index": chunk_index,
                        "results": [],
                        "stage": "initial",
                        "context_chunks": (
                            context_chunks if len(context_chunks) > 1 else None
                        ),
                    },
                    stream_mode=["custom", "values"],
                ):
                    mode, data = stream_data

                    if mode == "custom":
                        # These are the real-time events pushed synchronously
                        # by writer() inside each node — received here as soon
                        # as they are pushed, without waiting for the node to finish.
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

                    # suppress raw state snapshots — they clutter the output

        # --- DEEP ANALYSIS RESULTS ---
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


async def main():
    if len(sys.argv) != 2:
        print("Usage: python streaming_log_analyzer.py <log_file_path>")
        sys.exit(1)

    log_file = sys.argv[1]
    analyzer = ContextualAnalyzer()
    await analyzer.process_file(log_file)


if __name__ == "__main__":
    asyncio.run(main())
