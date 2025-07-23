from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import AnyMessage, add_messages
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Shared model instance
model = ChatOpenAI(model="o3-mini")


# Shared state definition
class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    arxiv_id: str
    paper_content: str
    high_level_summary: str
    detailed_summary: str
    applications: str
    final_report: str


class InputState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


class OutputState(TypedDict):
    final_report: str
