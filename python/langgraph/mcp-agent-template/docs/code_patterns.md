# Common Code Patterns and Conventions

This document outlines recurring code patterns and conventions used throughout the `langgraph-mcp` project. Understanding these patterns is crucial for diagnostics and enhancements.

## 1. LangGraph Node Implementation (LLM Interaction)

Nodes within the LangGraph graphs that involve Large Language Model (LLM) calls generally follow this pattern:

```python
async def planner(state: State, *, config: RunnableConfig) -> dict[str, list[BaseMessage]]:
    # 1. Get Configuration: Load strategy-specific config
    configuration = Configuration.from_runnable_config(config)
    
    # 2. Define Prompt Template: Use ChatPromptTemplate with system prompt and placeholders
    prompt = ChatPromptTemplate.from_messages([
        ("system", configuration.planner_system_prompt),
        ("placeholder", "{messages}"),
        # Potentially other placeholders like {experts}, {plan}, {task}, {retrieved_docs}...
    ])
    
    # 3. Load LLM: Use the common utility function
    model = load_chat_model(configuration.planner_model)
    
    # 4. Prepare Context: Gather necessary data from state and config
    experts = configuration.build_experts_context()
    current_plan = state.planner_result.plan if state.planner_result else []
    
    # 5. Invoke Prompt: Format the prompt with the context
    context = await prompt.ainvoke({
        "messages": state.messages,
        "experts": experts,
        "plan": current_plan,
        "system_time": datetime.now(tz=timezone.utc).isoformat(),
    }, config)
    
    # 6. Invoke Model (Potentially with Structured Output):
    # Use .with_structured_output(PydanticModel) if expecting specific format
    response = await model.with_structured_output(PlannerResult).ainvoke(context, config)
    
    # 7. Prepare State Update: Create a dictionary with state keys to update
    result = {"planner_result": response}
    if response.clarification:
        result["messages"] = [AIMessage(content=response.clarification)]
        
    # 8. Return Update: LangGraph merges this dictionary into the state
    return result
```

**Key Steps:**

1.  **Configuration:** Each node receives the `RunnableConfig` and uses the strategy's `Configuration.from_runnable_config` method to access relevant settings (models, prompts, server configs).
2.  **Prompt Template:** `langchain_core.prompts.ChatPromptTemplate` is used to structure the input to the LLM, often combining a system prompt with placeholders for dynamic data like message history, task details, or retrieved documents.
3.  **Load LLM:** The `src.langgraph_mcp.utils.load_chat_model` utility function is consistently used to instantiate the LLM client based on a `provider/model` string from the configuration.
4.  **Context Preparation:** Data needed for the prompt placeholders is gathered from the current `state` and `configuration`.
5.  **Invoke Prompt:** The prompt template's `ainvoke` method formats the final input for the LLM.
6.  **Invoke Model:** The loaded model's `ainvoke` method is called. `.with_structured_output(PydanticModel)` is frequently used when the LLM is expected to return data matching a specific Pydantic schema (e.g., `PlannerResult`, `ExpertPrompt`, `TaskAssessmentResult`).
7.  **Prepare State Update:** The node returns a dictionary where keys match the fields in the graph's `State` class. LangGraph uses this dictionary to update the state.

## 2. Loading Language Models

### Chat Models

The `src/langgraph_mcp/utils.py:load_chat_model(fully_specified_name: str)` function provides a standardized way to load chat models:

*   It expects a `fully_specified_name` string in the format `"provider/model-name"` (e.g., `"openai/gpt-4o"`).
*   It parses the provider and model name.
*   It uses `langchain.chat_models.init_chat_model(model, model_provider=provider)` to instantiate the appropriate LangChain chat model client.

## 3. Human In The Loop (HITL)

### Motivation

In many real-world workflows, especially those involving ambiguous, incomplete, or high-risk decisions, it is necessary to insert **human judgment** at key points in the LangGraph agent flow. A common scenario is when a planner node determines that it lacks sufficient information or confidence to proceed — e.g., a tool call would be help but some required input arguments are not yet known from the conversation so far.

### Challenges

	- **Graph re-entry at the point-of-human-interaction:** Graph execution needs to pause at the point-of-interaction, and resume after receiving a human response at the point-of-interaction. For long graph-prefixes involving LLM calling nodes, there is non-determinism. Graph Executions starting from the beginning of the graph, after the human interactions, may not reach the point-of-interaction.

    - **Latency and Efficiency**: For large graphs or graphs that accumulate memory across steps, re-entry at the start node incurs unnecessary latency and token costs, particularly when LLM calls or tools are involved.

### Pattern and solution design

The solution to the above challenges is to use a **human input (HI) node**. Graph may conditionally route to the HI node when human input is required. The node logic expects the incoming edge source (node) to add the interaction prompt message before targetting the HI node. The HI node uses that message to prompt the human for input, using the **interrupt** pattern. Like python's `input` function (that prompts the user on `stdout`, waits for human input, and resumes after reading human input from `stdin`), the **interrupt** pushes the interrupt metadata in the graph state, prompts user with the interrupt message, awaits human message, resumes the graph execution at the interrupt point, and returns the human message. The HI node puts the human message in the graph state, and continues the graph execution engine. Here's its implementation in the simplest form.

```python
def human_input(state: State, *, config: RunnableConfig) -> dict[str, list[BaseMessage]]:
    last_message = state.messages[-1]
    human_message = interrupt(last_message.content)
    return {
        "messages": [HumanMessage(content=human_message)]
    }
```

Note that the client (sdk, or api) should invoke the graph with a command-resume.

E.g., SDK based resume:

```python
client.runs.stream(
    thread_id=thread_id,
    assistant_id=assistant_id,
    config=config,
    command=Command(resume="<received human input here>")
)
```

E.g., API based resume:

```http
POST {{lg_api_server}}/threads/{{thread_id}}/runs/stream
Content-Type: application/json
Accept: application/json

{
  "assistant_id": "{{assistant_id}}",
  "command": {
    "resume": "<received human input here>",
  },
  "config": {..}
}
```