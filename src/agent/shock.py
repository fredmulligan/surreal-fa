"""
Shock propagation agent — the product.
Takes an event/question and traces consequences through the knowledge graph.

Usage:
    python -m src.agent.shock "What happens if copper prices double?"
"""

import os
import sys
import json
from typing import Literal

from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from src.agent.state import ShockState
from src.agent.tools import search_polymarket
from src.graph.db import GraphDB
from src.graph.shock import ShockEngine
from src.graph.queries import GraphQueries

load_dotenv()


SHOCK_SYSTEM_PROMPT = """You are Surreal FA — a financial analysis agent that traces economic shockwaves.

Given a shock or "what if" question, you trace the consequences through a knowledge graph
of the real economy to find the surprising second- and third-order effects that analysts miss.

The knowledge graph contains companies, industries, technologies, commodities, government policies,
and the relationships between them (supply chains, competitors, complements, substitutes,
commodity inputs with cost sensitivities, etc).

Your job:
1. Parse the shock — what's actually changing? (a commodity price, a company event, a policy, a technology shift)
2. Check Polymarket for real probability data on this event
3. Use the graph tools to find directly affected entities (hop 1)
4. For each affected entity, trace outward — who depends on them? What commodities do they use? (hop 2)
5. Keep going — find the third-hop surprises that nobody is thinking about (hop 3+)
6. For each effect, explain the causal chain and estimate direction (positive/negative) and magnitude

The best insights are the ones furthest from the epicenter. "AI boom helps Nvidia" is boring.
"AI boom eventually squeezes toy bear manufacturers through copper prices" is surreal financial advice.

Current shock query: {query}
{probability_info}

Available graph stats:
{graph_stats}
"""


def create_shock_agent():
    """Create the shock propagation agent."""
    db = GraphDB()
    engine = ShockEngine(db)
    queries = GraphQueries(db)

    @tool
    def find_affected_by_commodity(commodity_name: str) -> str:
        """Find all companies that use a commodity as input.
        Returns companies with their cost sensitivity to this commodity."""
        result = engine.get_commodity_ripple(commodity_name)
        return json.dumps(result, indent=2, default=str)

    @tool
    def find_affected_by_industry_shock(industry_name: str) -> str:
        """Find all companies in an industry that would be affected by an industry-wide shock."""
        result = queries.companies_in_industry(industry_name)
        return json.dumps(result, indent=2, default=str)

    @tool
    def get_company_dependencies(company_name: str) -> str:
        """Get all dependencies for a company — supply chain, commodity inputs,
        technologies, complements, competitors. Shows what the company depends on
        and what depends on the company."""
        result = db.traverse("company", company_name.lower().replace(" ", "_"))
        return json.dumps(result, indent=2, default=str)

    @tool
    def get_supply_chain(company_name: str) -> str:
        """Get suppliers and customers of a company from the knowledge graph."""
        result = queries.supply_chain_of(company_name)
        return json.dumps(result, indent=2, default=str)

    @tool
    def find_substitute_commodities(commodity_name: str) -> str:
        """Find substitute commodities/inputs. If copper gets expensive,
        what can companies switch to?"""
        result = engine.get_substitute_options(commodity_name)
        return json.dumps(result, indent=2, default=str)

    @tool
    def get_second_order_effects(company_names: str) -> str:
        """Given a comma-separated list of company names, find their downstream
        dependencies — the second-order effects of those companies being affected."""
        names = [n.strip() for n in company_names.split(",")]
        result = engine.get_second_order(names)
        return json.dumps(result, indent=2, default=str)

    @tool
    def query_graph(surql_query: str) -> str:
        """Run a raw SurrealQL query against the knowledge graph.
        Use for custom traversals not covered by other tools.
        Example: SELECT ->supplies_to->company FROM company WHERE name = 'TSMC'"""
        result = db.query(surql_query)
        return json.dumps(result, indent=2, default=str)

    @tool
    def get_current_graph_stats() -> str:
        """Get summary statistics of the knowledge graph."""
        result = queries.graph_stats()
        return json.dumps(result, indent=2, default=str)

    all_tools = [
        find_affected_by_commodity,
        find_affected_by_industry_shock,
        get_company_dependencies,
        get_supply_chain,
        find_substitute_commodities,
        get_second_order_effects,
        query_graph,
        get_current_graph_stats,
        search_polymarket,
    ]

    llm = AzureChatOpenAI(
        azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview"),
        temperature=0.2,
    )
    llm_with_tools = llm.bind_tools(all_tools)

    def agent_node(state: ShockState) -> dict:
        stats_str = json.dumps(queries.graph_stats(), indent=2)

        probability_info = ""
        if state.get("polymarket_checked") and state.get("probability") is not None:
            probability_info = f"Polymarket probability: {state['probability']:.0%}"

        system_prompt = SHOCK_SYSTEM_PROMPT.format(
            query=state["query"],
            probability_info=probability_info,
            graph_stats=stats_str,
        )

        messages = state.get("messages", [])
        from langchain_core.messages import SystemMessage
        full_messages = [SystemMessage(content=system_prompt)] + messages

        response = llm_with_tools.invoke(full_messages)
        return {"messages": [response]}

    def should_continue(state: ShockState) -> Literal["tools", "__end__"]:
        messages = state.get("messages", [])
        if messages and hasattr(messages[-1], "tool_calls") and messages[-1].tool_calls:
            return "tools"
        return "__end__"

    workflow = StateGraph(ShockState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode(all_tools))

    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", "__end__": END})
    workflow.add_edge("tools", "agent")

    return workflow.compile()


def run_shock(query: str):
    agent = create_shock_agent()

    initial_state: ShockState = {
        "query": query,
        "messages": [],
        "cascade": {},
        "current_hop": 0,
        "max_hops": 4,
        "polymarket_checked": False,
        "probability": None,
    }

    print(f"\n{'='*60}")
    print(f"  Surreal FA — Shock Analysis")
    print(f"  Query: {query}")
    print(f"{'='*60}\n")

    final_response = ""
    for event in agent.stream(initial_state, {"recursion_limit": 50}):
        for key, value in event.items():
            if key == "agent":
                msgs = value.get("messages", [])
                for msg in msgs:
                    if hasattr(msg, "content") and msg.content:
                        final_response = msg.content
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tc in msg.tool_calls:
                            print(f"  -> Querying: {tc['name']}({tc['args']})")
            elif key == "tools":
                msgs = value.get("messages", [])
                for msg in msgs:
                    if hasattr(msg, "content"):
                        content = msg.content[:100] if isinstance(msg.content, str) else str(msg.content)[:100]
                        print(f"  <- {content}...")

    print(f"\n{'='*60}")
    print(f"  ANALYSIS")
    print(f"{'='*60}\n")
    print(final_response)


if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "What happens if copper prices double?"
    run_shock(query)
