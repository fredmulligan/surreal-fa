"""
Graph-building agent — the kitchen.
Iteratively discovers, enriches, and expands the knowledge graph.

Usage:
    python -m src.agent.build "Electric Vehicles"
"""

import os
import sys
from typing import Literal

from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from src.agent.state import BuildState
from src.agent.tools import DATA_TOOLS, make_graph_tools
from src.graph.db import GraphDB
from src.graph.builder import GraphBuilder

load_dotenv()

# ── System prompts ──

DISCOVER_PROMPT = """You are a financial research agent building a knowledge graph of the economy.

Your current task: DISCOVER companies, technologies, and commodities in the industry: "{query}"

Use your tools to:
1. Search for companies in this industry using Wikidata and yfinance
2. For each company found, look up its details (ticker, market cap, description)
3. Add each company to the knowledge graph, along with its industry
4. Identify key technologies used in this industry
5. Identify key commodity inputs (raw materials, energy)
6. Add technologies and commodities to the graph

Be thorough but efficient. Find at least 5-10 major players.
After discovering the main players, add them all to the graph.

Current graph state:
- Companies found so far: {companies_found}
- Industries found: {industries_found}
"""

ENRICH_PROMPT = """You are a financial research agent enriching a knowledge graph.

Your current task: ENRICH relationships between entities already in the graph.

Companies in the graph: {companies_found}
Industries: {industries_found}
Technologies: {technologies_found}
Commodities: {commodities_found}

For each company, determine and add relationships:
- Who COMPETES_WITH whom? (competitors in the same space)
- Who SUPPLIES_TO whom? (supply chain relationships)
- Who is a COMPLEMENT_OF whom? (companies that grow together, e.g. Shopify & Stripe)
- Who is a SUBSTITUTE_FOR whom? (companies that replace each other)
- Which company USES_TECHNOLOGY which technology?
- Which company USES_INPUT which commodity? Include cost_sensitivity if you can estimate it.
- Any SUBSIDIARY_OF or INVESTED_IN relationships?

Use your knowledge and the data tools to verify relationships.
Add each relationship to the graph using add_relationship_to_graph.

Properties matter — add cost_sensitivity, criticality, revenue_dependency where relevant.
These properties power the shock propagation engine.
"""

EXPAND_PROMPT = """You are a financial research agent expanding a knowledge graph.

Your current task: EXPAND the graph into adjacent industries and discover new connections.

Current graph:
- Companies: {companies_found}
- Industries: {industries_found}
- Technologies: {technologies_found}
- Commodities: {commodities_found}

Look at the edges of the current graph and expand outward:
1. What adjacent industries supply inputs to or consume outputs from the mapped industries?
2. What commodities are shared across multiple industries?
3. What government policies or subsidies affect these industries?
4. Are there companies in other industries that would be affected by shocks to this graph?

Add the new nodes and relationships to the graph. The goal is to make the graph
dense enough that shock propagation reveals surprising multi-hop effects.
"""


def create_build_agent(query: str):
    """Create and return the graph-building agent."""
    db = GraphDB()
    builder = GraphBuilder(db)
    graph_tools = make_graph_tools(builder)
    all_tools = DATA_TOOLS + graph_tools

    llm = AzureChatOpenAI(
        azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview"),
        temperature=0,
    )
    llm_with_tools = llm.bind_tools(all_tools)

    def get_prompt(state: BuildState) -> str:
        phase = state.get("phase", "discover")
        kwargs = {
            "query": state["query"],
            "companies_found": ", ".join(state.get("companies_found", [])) or "none yet",
            "industries_found": ", ".join(state.get("industries_found", [])) or "none yet",
            "technologies_found": ", ".join(state.get("technologies_found", [])) or "none yet",
            "commodities_found": ", ".join(state.get("commodities_found", [])) or "none yet",
        }
        if phase == "discover":
            return DISCOVER_PROMPT.format(**kwargs)
        elif phase == "enrich":
            return ENRICH_PROMPT.format(**kwargs)
        elif phase == "expand":
            return EXPAND_PROMPT.format(**kwargs)
        return "You have completed the graph building. Summarize what was built."

    def agent_node(state: BuildState) -> dict:
        """The main agent reasoning node."""
        prompt = get_prompt(state)
        messages = state.get("messages", [])
        if not messages or messages[0].content != prompt:
            from langchain_core.messages import SystemMessage
            messages = [SystemMessage(content=prompt)] + messages

        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    def should_continue(state: BuildState) -> Literal["tools", "next_phase"]:
        """Check if the agent wants to use tools or move to next phase."""
        messages = state.get("messages", [])
        if messages and hasattr(messages[-1], "tool_calls") and messages[-1].tool_calls:
            return "tools"
        return "next_phase"

    def advance_phase(state: BuildState) -> dict:
        """Move to the next phase of graph building."""
        phase = state.get("phase", "discover")
        iteration = state.get("iteration", 0)
        max_iter = state.get("max_iterations", 3)

        if phase == "discover":
            return {"phase": "enrich", "messages": [], "iteration": iteration + 1}
        elif phase == "enrich":
            return {"phase": "expand", "messages": [], "iteration": iteration + 1}
        elif phase == "expand":
            if iteration + 1 < max_iter:
                # Loop back to enrich with the expanded graph
                return {"phase": "enrich", "messages": [], "iteration": iteration + 1}
            return {"phase": "done", "messages": []}
        return {"phase": "done"}

    def is_done(state: BuildState) -> Literal["agent", "__end__"]:
        """Check if we should keep going or stop."""
        if state.get("phase") == "done":
            return "__end__"
        return "agent"

    # Build the graph
    workflow = StateGraph(BuildState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode(all_tools))
    workflow.add_node("advance", advance_phase)

    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", "next_phase": "advance"})
    workflow.add_edge("tools", "agent")
    workflow.add_conditional_edges("advance", is_done, {"agent": "agent", "__end__": END})

    compiled = workflow.compile()
    return compiled, db


def run_build(query: str, max_iterations: int = 3):
    """Run the graph-building agent."""
    agent, db = create_build_agent(query)

    initial_state: BuildState = {
        "query": query,
        "messages": [],
        "phase": "discover",
        "companies_found": [],
        "industries_found": [],
        "technologies_found": [],
        "commodities_found": [],
        "iteration": 0,
        "max_iterations": max_iterations,
    }

    print(f"\n{'='*60}")
    print(f"  Surreal FA — Building graph for: {query}")
    print(f"{'='*60}\n")

    # Stream so we can watch it work
    for event in agent.stream(initial_state, {"recursion_limit": 100}):
        for key, value in event.items():
            if key == "agent":
                msgs = value.get("messages", [])
                for msg in msgs:
                    if hasattr(msg, "content") and msg.content:
                        print(f"\n[Agent] {msg.content[:200]}...")
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tc in msg.tool_calls:
                            print(f"  -> Calling: {tc['name']}({tc['args']})")
            elif key == "tools":
                msgs = value.get("messages", [])
                for msg in msgs:
                    if hasattr(msg, "content"):
                        content = msg.content[:150] if isinstance(msg.content, str) else str(msg.content)[:150]
                        print(f"  <- Result: {content}...")
            elif key == "advance":
                phase = value.get("phase", "?")
                print(f"\n{'='*40}")
                print(f"  Phase: {phase}")
                print(f"{'='*40}")

    print(f"\n{'='*60}")
    print(f"  Graph building complete!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "Electric Vehicles"
    run_build(query)
