"""
Applications Agent

This agent is responsible for generating a summary of the real-world applications of the paper.
"""

from shared import State, model
from prompts.prompts import APPLICATION_PROMPT
from langgraph.graph import StateGraph, START, END


async def applications_node(state: State):
    response = await model.ainvoke(
        APPLICATION_PROMPT.format(paper_text=state["paper_content"])
    )
    return {"applications": response.content}


applications_workflow = StateGraph(State)
applications_workflow.add_node("applications", applications_node)
applications_workflow.add_edge(START, "applications")
applications_workflow.add_edge("applications", END)

applications_agent = applications_workflow.compile()
