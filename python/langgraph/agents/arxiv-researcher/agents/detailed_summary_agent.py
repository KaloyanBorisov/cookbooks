"""
Detailed Summary Agent

This agent is responsible for generating a detailed summary of the paper.
"""

from shared import State, model
from prompts.prompts import DETAILED_SUMMARY_PROMPT
from langgraph.graph import StateGraph, START, END


async def detailed_summary_node(state: State):
    response = await model.ainvoke(
        DETAILED_SUMMARY_PROMPT.format(paper_text=state["paper_content"])
    )
    return {"detailed_summary": response.content}


detailed_summary_workflow = StateGraph(State)
detailed_summary_workflow.add_node("detailed_summary", detailed_summary_node)
detailed_summary_workflow.add_edge(START, "detailed_summary")
detailed_summary_workflow.add_edge("detailed_summary", END)

detailed_summary_agent = detailed_summary_workflow.compile()
