from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict
from langchain_openai import ChatOpenAI
import json
import os
from dotenv import load_dotenv


load_dotenv()


class InputState(TypedDict):
    question: str


class OutputState(TypedDict):
    answer: str


class OverallState(InputState, OutputState):
    pass


def load_finance_data():
    # Get the absolute path to the finance_data.json file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    finance_data_path = os.path.join(current_dir, "finance_data.json")

    # Load the finance data from the JSON file
    with open(finance_data_path, "r") as file:
        finance_data = json.load(file)

    return finance_data


def answer_node(state: InputState):
    # Load the finance data
    finance_data = load_finance_data()

    # Create a finance expert prompt
    finance_expert_prompt = """You are an expert financial analyst with deep knowledge of business contracts and financial planning.
    You have access to a dataset of company contracts containing information about:
    - Company names
    - Contract amounts
    - Contract lengths (in months)
    - Renewal dates
    
    Please analyze this data to provide helpful, accurate, and insightful answers to the user's questions.
    
    The user's question is: {question}
    """

    # Initialize the ChatOpenAI model
    llm = ChatOpenAI(model="gpt-4o-mini")

    # Call the model with the finance expert prompt and context
    response = llm.invoke(
        finance_expert_prompt.format(question=state["question"])
        + "\n\nHere is the finance data to reference: "
        + json.dumps(finance_data, indent=2)
    )

    # Return the answer along with the original question
    return {"answer": response.content, "question": state["question"]}


# Build the graph with explicit schemas
builder = StateGraph(OverallState, input=InputState, output=OutputState)
builder.add_node(answer_node)
builder.add_edge(START, "answer_node")
builder.add_edge("answer_node", END)
graph = builder.compile()
