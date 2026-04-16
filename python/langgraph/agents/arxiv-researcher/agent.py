"""
arXiv Researcher Agent

This agent downloads and parses an arXiv paper given a URL and generates a summary report.
"""

from utils import extract_arxiv_id, download_arxiv_pdf_text
from shared import State, InputState, OutputState
from agents.high_level_summary_agent import high_level_summary_agent
from agents.detailed_summary_agent import detailed_summary_agent
from agents.application_agent import applications_agent
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END


async def extract_id_node(state: State):
    """Extract arXiv ID from user input"""
    user_message = ""
    for message in state["messages"]:
        if isinstance(message, HumanMessage):
            content = message.content
            if isinstance(content, list):
                user_message = " ".join(
                    part["text"] if isinstance(part, dict) else str(part)
                    for part in content
                )
            else:
                user_message = content
            break

    try:
        arxiv_id = await extract_arxiv_id(user_message)
        return {
            "arxiv_id": arxiv_id,
            "messages": [AIMessage(content=f"Extracted arXiv ID: {arxiv_id}")],
        }
    except ValueError as e:
        return {"messages": [AIMessage(content=f"Error extracting arXiv ID: {str(e)}")]}


async def download_paper(state: State):
    """Download and parse the arXiv paper"""
    arxiv_id = state.get("arxiv_id", "")
    if not arxiv_id:
        return {"messages": [AIMessage(content="No arXiv ID found to download paper")]}

    try:
        paper_content = await download_arxiv_pdf_text(arxiv_id)
        return {
            "paper_content": paper_content,
            "messages": [
                AIMessage(
                    content=f"Successfully downloaded and parsed paper {arxiv_id}. Ready for analysis."
                )
            ],
        }
    except Exception as e:
        return {"messages": [AIMessage(content=f"Error downloading paper: {str(e)}")]}


def should_download(state: State):
    """Check if we have arxiv_id to proceed to download"""
    if state.get("arxiv_id"):
        return "download"
    return "end"


def aggregate(state: State):
    """Aggregate all summaries into final report"""
    final_report = f"""# arXiv Paper Summary

        ## High Level Summary

        {state.get("high_level_summary", "")}

        ## Detailed Summary

        {state.get("detailed_summary", "")}

        ## Real World Applications

        {state.get("applications", "")}
        """

    return {"final_report": final_report, "messages": [AIMessage(content=final_report)]}


async def run_high_level_summary(state: State):
    """Wrapper to run high level summary subgraph"""
    result = await high_level_summary_agent.ainvoke(state)
    return {"high_level_summary": result["high_level_summary"]}


async def run_detailed_summary(state: State):
    """Wrapper to run detailed summary subgraph"""
    result = await detailed_summary_agent.ainvoke(state)
    return {"detailed_summary": result["detailed_summary"]}


async def run_applications(state: State):
    """Wrapper to run applications subgraph"""
    result = await applications_agent.ainvoke(state)
    return {"applications": result["applications"]}


workflow = StateGraph(State, input_schema=InputState, output_schema=OutputState)

# Add all nodes
workflow.add_node("extract_id", extract_id_node)
workflow.add_node("download_paper", download_paper)
workflow.add_node("aggregate", aggregate)
workflow.add_node("high_level_summary", run_high_level_summary)
workflow.add_node("detailed_summary", run_detailed_summary)
workflow.add_node("application", run_applications)

# Extract arXiv ID
workflow.add_edge(START, "extract_id")
workflow.add_conditional_edges(
    "extract_id",
    should_download,
    {
        "download": "download_paper",
        "end": END,
    },
)

# After downloading, run all three agents in parallel
workflow.add_edge("download_paper", "high_level_summary")
workflow.add_edge("download_paper", "detailed_summary")
workflow.add_edge("download_paper", "application")

# All specialist agents feed into aggregate
workflow.add_edge("high_level_summary", "aggregate")
workflow.add_edge("detailed_summary", "aggregate")
workflow.add_edge("application", "aggregate")
workflow.add_edge("aggregate", END)

# Compile
app = workflow.compile()
