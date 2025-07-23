"""
High Level Summary Agent

This agent is responsible for generating a high-level summary of the paper.
"""

from shared import State, model
from prompts.prompts import HIGH_LEVEL_SUMMARY_PROMPT
from langgraph.graph import StateGraph, START, END


async def high_level_summary_node(state: State):
    response = await model.ainvoke(
        HIGH_LEVEL_SUMMARY_PROMPT.format(paper_text=state["paper_content"])
    )
    return {"high_level_summary": response.content}


high_level_summary_workflow = StateGraph(State)
high_level_summary_workflow.add_node("high_level_summary", high_level_summary_node)
high_level_summary_workflow.add_edge(START, "high_level_summary")
high_level_summary_workflow.add_edge("high_level_summary", END)

high_level_summary_agent = high_level_summary_workflow.compile()
