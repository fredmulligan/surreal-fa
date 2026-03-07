# LangChain / LangGraph Cheat Sheet for Surreal FA

Read this on the train Saturday morning. 15 minutes max.

## What's What

**LangChain** = the toolkit. LLM calls, prompts, tools, output parsing. Think of it as the parts.

**LangGraph** = the state machine that connects the parts. You define nodes (functions), edges (transitions), and conditions (when to go where). It's how you build an agent that loops: think → act → observe → think again.

**LangChain Community** = extra integrations (SurrealDB, various LLMs, etc.)

**LangSmith** = observability/tracing. Useful for debugging agent loops. Free tier.

## The 5 Things You Actually Need

### 1. Tools — giving the LLM abilities

```python
from langchain_core.tools import tool

@tool
def search_company(name: str) -> str:
    """Search for a company by name. Returns company data."""  # <-- this docstring IS the tool description the LLM sees
    result = do_lookup(name)
    return json.dumps(result)
```

The `@tool` decorator turns a function into something an LLM can call. The docstring matters — it's what the LLM reads to decide when to use the tool.

### 2. LLM with Tools — connecting them

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o", temperature=0)
llm_with_tools = llm.bind_tools([search_company, add_to_graph, ...])

# Now when you call the LLM, it can choose to use tools
response = llm_with_tools.invoke([
    SystemMessage(content="You are a research agent..."),
    HumanMessage(content="Find Tesla's competitors"),
])

# response.tool_calls contains any tools it wants to call
```

### 3. StateGraph — the agent loop

```python
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict
from typing import Annotated
from langgraph.graph import add_messages

# Define what the agent remembers between steps
class MyState(TypedDict):
    messages: Annotated[list, add_messages]  # conversation history
    phase: str                                # custom state

# Create the graph
workflow = StateGraph(MyState)

# Add nodes (functions that transform state)
workflow.add_node("agent", agent_function)
workflow.add_node("tools", ToolNode(my_tools))

# Add edges (transitions)
workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue, {
    "tools": "tools",     # if LLM wants to call a tool
    "__end__": END,        # if LLM is done
})
workflow.add_edge("tools", "agent")  # after running tool, go back to agent

# Compile and run
app = workflow.compile()
result = app.invoke({"messages": [...], "phase": "discover"})
```

### 4. The Agent-Tool Loop

This is the core pattern. The agent thinks, decides to use a tool, gets the result, thinks again:

```
START → agent thinks → wants tool? → yes → run tool → back to agent
                                    → no  → END (output final answer)
```

In code:

```python
def should_continue(state):
    """Does the LLM want to call a tool?"""
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return "__end__"
```

`ToolNode` from `langgraph.prebuilt` handles running the tools and returning results automatically.

### 5. Streaming — watching it work

```python
for event in app.stream(initial_state, {"recursion_limit": 50}):
    for node_name, output in event.items():
        print(f"Node '{node_name}' produced: {output}")
```

Each event tells you which node just ran and what it produced. Use this to show the agent working in real time.

## Key Patterns for Surreal FA

### Multi-phase agent (what our build agent does)

```python
def advance_phase(state):
    if state["phase"] == "discover":
        return {"phase": "enrich"}
    elif state["phase"] == "enrich":
        return {"phase": "expand"}
    else:
        return {"phase": "done"}
```

The agent cycles through phases. Each phase has a different system prompt telling it what to focus on.

### Tool output → state update

When a tool runs, its output goes back as a ToolMessage in the conversation. The LLM sees it and decides what to do next. You don't need to manually parse tool results.

### Recursion limit

```python
app.invoke(state, {"recursion_limit": 50})
```

Safety valve. Each node execution counts as one step. Default is 25. Set higher for complex agent loops.

## Messages

```python
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage

# System message = instructions to the LLM
SystemMessage(content="You are a research agent...")

# Human message = user input
HumanMessage(content="Map the EV industry")

# AI message = LLM response (may include tool_calls)
# ToolMessage = result of a tool call (created automatically by ToolNode)
```

## SurrealDB + LangChain

The `langchain-surrealdb` package gives you `SurrealDBVectorStore` for RAG/vector search. We're using SurrealDB primarily as a **graph database** through its native query language (SurrealQL), so our integration is through the `surrealdb` Python SDK directly.

```python
from surrealdb import Surreal

db = Surreal("ws://localhost:8000/rpc")
await db.connect()
await db.signin({"username": "root", "password": "root"})
await db.use("surreal_fa", "surreal_fa")

# Create nodes
await db.query("CREATE company:tesla SET name = 'Tesla', ticker = 'TSLA'")

# Create relationships (this is the graph part)
await db.query("RELATE company:tesla->operates_in->industry:electric_vehicles")

# Traverse the graph
await db.query("SELECT ->operates_in->industry FROM company:tesla")

# Multi-hop traversal (THIS is the magic for shock propagation)
await db.query("""
    SELECT ->demand_driver->industry<-operates_in<-company->uses_input->commodity
    FROM event WHERE name = 'AI Boom'
""")
```

## Common Gotchas

1. **Tool docstrings matter** — the LLM reads them to decide which tool to use. Be specific.
2. **asyncio.run() in tools** — if your tools are sync but call async SurrealDB code, wrap with `asyncio.run()`
3. **Recursion limit** — if your agent stops unexpectedly, increase the limit
4. **Temperature** — use 0 for reliable tool use, 0.2-0.5 for creative reasoning (shock analysis)
5. **System prompt per phase** — change the system message based on what phase the agent is in

## Quick Reference

| Thing | Import |
|-------|--------|
| `@tool` decorator | `from langchain_core.tools import tool` |
| `ChatOpenAI` | `from langchain_openai import ChatOpenAI` |
| `StateGraph` | `from langgraph.graph import StateGraph, START, END` |
| `ToolNode` | `from langgraph.prebuilt import ToolNode` |
| `add_messages` | `from langgraph.graph import add_messages` |
| Messages | `from langchain_core.messages import SystemMessage, HumanMessage` |
| SurrealDB | `from surrealdb import Surreal` |

## Install

```bash
pip install langchain langgraph langchain-openai langchain-community surrealdb yfinance
```

## Resources

- LangGraph docs: https://docs.langchain.com/oss/python/langgraph/overview
- SurrealDB docs: https://surrealdb.com/docs
- SurrealDB LangChain integration: https://surrealdb.com/docs/integrations/frameworks/langchain
