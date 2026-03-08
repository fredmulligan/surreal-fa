"""
LangChain tools that agents can use.
These wrap the connectors and graph operations into tool-callable functions.
"""

import json
from langchain_core.tools import tool

from src.connectors.yfinance_connector import get_company_info, get_company_by_name, get_key_stats
from src.connectors.wikidata_connector import (
    get_companies_in_industry,
    get_company_relationships,
    get_supply_chain,
    search_entity,
)
from src.connectors.polymarket_connector import search_events, search_markets


# ── Data source tools ──

@tool
def lookup_company_by_ticker(ticker: str) -> str:
    """Look up a company by its stock ticker symbol. Returns company info including
    name, description, market cap, revenue, sector, industry, and more."""
    info = get_company_info(ticker)
    if info:
        return json.dumps(info, indent=2, default=str)
    return f"No company found for ticker {ticker}"


@tool
def search_company_by_name(name: str) -> str:
    """Search for a company by name. Returns company info if found."""
    info = get_company_by_name(name)
    if info:
        return json.dumps(info, indent=2, default=str)
    return f"No company found for name '{name}'"


@tool
def get_company_financials(ticker: str) -> str:
    """Get financial stats for a company (margins, revenue growth, cost structure).
    Useful for understanding cost sensitivity to commodity prices."""
    stats = get_key_stats(ticker)
    if stats:
        return json.dumps(stats, indent=2, default=str)
    return f"No financial stats found for {ticker}"


@tool
def find_companies_in_industry_wikidata(industry_name: str) -> str:
    """Find companies in an industry using Wikidata's structured knowledge graph.
    Returns companies with their Wikidata IDs, tickers, countries."""
    companies = get_companies_in_industry(industry_name)
    if companies:
        return json.dumps(companies[:20], indent=2, default=str)
    return f"No companies found in industry '{industry_name}' on Wikidata"


@tool
def get_company_wikidata_relationships(wikidata_id: str) -> str:
    """Get structured relationships for a company from Wikidata.
    Pass a Wikidata Q-ID (e.g. 'Q478214' for Tesla).
    Returns parent companies, subsidiaries, products, founders, CEO, etc."""
    rels = get_company_relationships(wikidata_id)
    if rels:
        return json.dumps(rels, indent=2, default=str)
    return f"No relationships found for Wikidata ID {wikidata_id}"


@tool
def get_company_supply_chain_wikidata(wikidata_id: str) -> str:
    """Get supply chain data for a company from Wikidata.
    Returns what the company produces, uses, and who supplies them."""
    chain = get_supply_chain(wikidata_id)
    if any(chain.values()):
        return json.dumps(chain, indent=2, default=str)
    return f"No supply chain data found for Wikidata ID {wikidata_id}"


@tool
def search_wikidata_entity(name: str) -> str:
    """Search Wikidata for an entity by name. Returns matching entities with
    their Q-IDs and descriptions. Use this to find Wikidata IDs for companies,
    technologies, commodities, etc."""
    results = search_entity(name)
    if results:
        return json.dumps(results, indent=2, default=str)
    return f"No Wikidata entities found for '{name}'"


@tool
def search_polymarket(query: str) -> str:
    """Search Polymarket for prediction markets related to a query.
    Returns events with their current probabilities.
    Use this to find real-world probabilities for economic events."""
    events = search_events(query)
    if events:
        return json.dumps(events[:5], indent=2, default=str)
    markets = search_markets(query)
    if markets:
        return json.dumps(markets[:5], indent=2, default=str)
    return f"No Polymarket events found for '{query}'"


# ── Graph operation tools ──

def make_graph_tools(builder):
    """Create graph-writing tools bound to a specific GraphBuilder instance."""

    @tool
    def add_company_to_graph(name: str, ticker: str = "", description: str = "", market_cap: float = 0, hq_country: str = "", industry: str = "") -> str:
        """Add a company to the knowledge graph. If an industry is provided,
        also creates the industry node and links them."""
        data = {"name": name, "ticker": ticker, "description": description,
                "market_cap": market_cap if market_cap else None,
                "hq_country": hq_country if hq_country else None, "source": "agent"}
        company_id = builder.add_company(data)
        if industry:
            industry_id = builder.add_industry(industry)
            builder.link_company_to_industry(company_id, industry_id)
        return f"Added company '{name}' to graph as {company_id}" + (f" in industry '{industry}'" if industry else "")

    @tool
    def add_relationship_to_graph(
        from_name: str,
        from_type: str,
        relationship: str,
        to_name: str,
        to_type: str,
        properties: str = "{}"
    ) -> str:
        """Add a relationship between two entities in the knowledge graph.
        from_type/to_type: company, industry, technology, commodity, policy, event, product
        relationship: operates_in, competes_with, supplies_to, complement_of, substitute_for,
                      subsidiary_of, uses_technology, invested_in, uses_input, substitute_input,
                      demand_driver, affected_by_policy, produces
        properties: JSON string of edge properties like '{"cost_sensitivity": 0.8}'"""
        props = json.loads(properties) if properties != "{}" else None
        from_id = from_name.lower().replace(" ", "_")
        to_id = to_name.lower().replace(" ", "_")
        builder.db.create_relationship(from_type, from_id, relationship, to_type, to_id, props)
        return f"Created {from_name} -[{relationship}]-> {to_name}"

    @tool
    def add_technology_to_graph(name: str, maturity: str = "", description: str = "") -> str:
        """Add a technology to the knowledge graph.
        maturity: emerging, growing, mature, declining"""
        builder.add_technology(name, {"maturity": maturity, "description": description})
        return f"Added technology '{name}' to graph"

    @tool
    def add_commodity_to_graph(name: str, category: str = "", description: str = "") -> str:
        """Add a commodity/raw material to the knowledge graph.
        category: metal, energy, agricultural, chemical"""
        builder.add_commodity(name, {"category": category, "description": description})
        return f"Added commodity '{name}' to graph"

    @tool
    def add_policy_to_graph(name: str, policy_type: str = "", region: str = "", description: str = "") -> str:
        """Add a government policy/subsidy to the knowledge graph.
        policy_type: subsidy, tariff, regulation, tax_credit, ban"""
        builder.add_policy(name, {"policy_type": policy_type, "region": region, "description": description})
        return f"Added policy '{name}' to graph"

    @tool
    def add_event_to_graph(name: str, event_type: str = "", description: str = "", probability: float = 0) -> str:
        """Add an event/shock to the knowledge graph.
        event_type: market_shock, geopolitical, technology_shift, regulation"""
        data = {"event_type": event_type, "description": description}
        if probability > 0:
            data["probability"] = probability
        builder.add_event(name, data)
        return f"Added event '{name}' to graph"

    @tool
    def get_graph_stats() -> str:
        """Get current stats of the knowledge graph — how many companies, industries,
        relationships, etc. Useful for understanding what's already been mapped."""
        from src.graph.queries import GraphQueries
        queries = GraphQueries(builder.db)
        stats = queries.graph_stats()
        return json.dumps(stats, indent=2)

    return [
        add_company_to_graph,
        add_relationship_to_graph,
        add_technology_to_graph,
        add_commodity_to_graph,
        add_policy_to_graph,
        add_event_to_graph,
        get_graph_stats,
    ]


# All data source tools (no graph dependency)
DATA_TOOLS = [
    lookup_company_by_ticker,
    search_company_by_name,
    get_company_financials,
    find_companies_in_industry_wikidata,
    get_company_wikidata_relationships,
    get_company_supply_chain_wikidata,
    search_wikidata_entity,
    search_polymarket,
]
