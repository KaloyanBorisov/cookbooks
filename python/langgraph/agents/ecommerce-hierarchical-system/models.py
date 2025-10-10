from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

# Central model configuration for all agents
model = ChatOpenAI(model="gpt-4o", temperature=0)
