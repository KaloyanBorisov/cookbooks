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
        self.chunk_buffer = deque(maxlen=3)

    def _build_graph(self):
        async def error_scan(state: State, config):
            writer = get_stream_writer()
            writer(
                {
                    "type": "progress",
                    "chunk": state["chunk_index"],
                    "stage": "error_scan",
                }
            )

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
                return {
                    "stage": "complete",
                    "results": state["results"] + ["No issues found"],
                }

        async def deep_contextual_analysis(state: State, config):
            writer = get_stream_writer()
            writer(
                {
                    "type": "progress",
                    "chunk": state["chunk_index"],
                    "stage": "deep_analysis",
                }
            )

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
            return {
                "stage": "complete",
                "results": state["results"] + [response.content],
            }

        workflow = StateGraph(State)
        workflow.add_node("error_scan", error_scan)
        workflow.add_node("deep_analysis", deep_contextual_analysis)

        workflow.add_edge(START, "error_scan")

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
        context_chunks = []
        buffer_list = list(self.chunk_buffer)

        if len(buffer_list) >= 2:
            context_chunks = buffer_list[-2:]
        if len(buffer_list) == 3:
            context_chunks = buffer_list

        return context_chunks

    async def process_file(self, file_path: str):
        print(f"Processing: {file_path}")

        loader = TextLoader(file_path)
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        chunk_index = 0

        for document in loader.lazy_load():
            for chunk in splitter.split_documents([document]):
                chunk_index += 1
                chunk_content = chunk.page_content

                self.chunk_buffer.append(chunk_content)
                context_chunks = self._get_context_chunks(chunk_index)

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
                        if data.get("type") == "progress":
                            stage = data.get("stage", "unknown")
                            print(f"[{stage.upper()}] Processing chunk {data['chunk']}")

                        elif data.get("type") == "error_detected":
                            print(
                                f"ERROR DETECTED in chunk {data['chunk']} - Expanding context for analysis"
                            )

                        elif data.get("type") == "clean_chunk":
                            print(f"Chunk {data['chunk']} - No issues")

                        elif data.get("type") == "detailed_analysis":
                            print(f"\nDETAILED ANALYSIS (Chunk {chunk_index}):")
                            print("-" * 50)
                            print(data["content"])
                            print("-" * 50)

                    elif mode == "values":
                        print("\n--- STATE SNAPSHOT ---")
                        print(data)
                        print("---------------------\n")


async def main():
    if len(sys.argv) != 2:
        print("Usage: python streaming_log_analyzer.py <log_file_path>")
        sys.exit(1)

    log_file = sys.argv[1]
    analyzer = ContextualAnalyzer()
    await analyzer.process_file(log_file)


if __name__ == "__main__":
    asyncio.run(main())
