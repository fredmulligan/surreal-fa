"""
Pre-built graph queries for common operations.
Used by the shock propagation agent and the query interface.
"""

from src.graph.db import GraphDB


class GraphQueries:
    """Canned queries for the knowledge graph."""

    def __init__(self, db: GraphDB | None = None):
        self.db = db or GraphDB()

    async def companies_in_industry(self, industry_name: str) -> list[dict]:
        """Get all companies operating in an industry."""
        result = await self.db.query("""
            SELECT <-operates_in<-company.* AS companies
            FROM industry WHERE name = $name
        """, {"name": industry_name})
        if result and result[0].get("result"):
            return result[0]["result"]
        return []

    async def competitors_of(self, company_name: str) -> list[dict]:
        """Get competitors of a company."""
        result = await self.db.query("""
            SELECT ->competes_with->company.* AS competitors
            FROM company WHERE name = $name
        """, {"name": company_name})
        if result and result[0].get("result"):
            return result[0]["result"]
        return []

    async def supply_chain_of(self, company_name: str) -> dict:
        """Get suppliers and customers of a company."""
        result = await self.db.query("""
            SELECT
                ->supplies_to->company.* AS customers,
                <-supplies_to<-company.* AS suppliers
            FROM company WHERE name = $name
        """, {"name": company_name})
        if result and result[0].get("result"):
            return result[0]["result"][0] if result[0]["result"] else {}
        return {}

    async def commodity_dependents(self, commodity_name: str) -> list[dict]:
        """Find all companies that use a commodity as input."""
        result = await self.db.query("""
            SELECT <-uses_input<-company.* AS companies
            FROM commodity WHERE name = $name
        """, {"name": commodity_name})
        if result and result[0].get("result"):
            return result[0]["result"]
        return []

    async def shock_cascade(self, event_name: str, depth: int = 3) -> dict:
        """
        Trace a shock from an event through the graph.
        Returns a nested structure of consequences at each hop.
        """
        cascade = {"event": event_name, "hops": []}

        # Hop 1: Event → directly affected industries
        hop1 = await self.db.query("""
            SELECT
                ->demand_driver->industry.{name, id} AS industries
            FROM event WHERE name = $name
        """, {"name": event_name})
        if hop1 and hop1[0].get("result"):
            industries = hop1[0]["result"]
            cascade["hops"].append({"depth": 1, "type": "industries", "data": industries})

        # Hop 2: Industries → companies in those industries
        hop2 = await self.db.query("""
            SELECT
                ->demand_driver->industry<-operates_in<-company.{name, ticker, market_cap, id} AS companies
            FROM event WHERE name = $name
        """, {"name": event_name})
        if hop2 and hop2[0].get("result"):
            companies = hop2[0]["result"]
            cascade["hops"].append({"depth": 2, "type": "companies", "data": companies})

        # Hop 3: Companies → their commodity inputs, supply chains, technologies
        hop3 = await self.db.query("""
            SELECT
                ->demand_driver->industry<-operates_in<-company->uses_input->commodity.{name, id} AS commodities,
                ->demand_driver->industry<-operates_in<-company->supplies_to->company.{name, ticker, id} AS downstream,
                ->demand_driver->industry<-operates_in<-company->uses_technology->technology.{name, id} AS technologies
            FROM event WHERE name = $name
        """, {"name": event_name})
        if hop3 and hop3[0].get("result"):
            cascade["hops"].append({"depth": 3, "type": "dependencies", "data": hop3[0]["result"]})

        return cascade

    async def find_path(self, from_name: str, to_name: str) -> list[dict]:
        """Find connection paths between two entities."""
        # SurrealDB doesn't have native shortest path yet,
        # so we do a breadth-first check of common relationship types
        result = await self.db.query("""
            SELECT * FROM company WHERE name = $from;
            SELECT * FROM company WHERE name = $to;
        """, {"from": from_name, "to": to_name})
        # This is a simplified version — the LLM agent will do smarter traversal
        return result

    async def graph_stats(self) -> dict:
        """Get a summary of what's in the graph."""
        stats = {}
        for table in ["company", "industry", "technology", "commodity", "policy", "event"]:
            result = await self.db.query(f"SELECT count() AS count FROM {table} GROUP ALL")
            if result and result[0].get("result"):
                stats[table] = result[0]["result"][0].get("count", 0) if result[0]["result"] else 0
            else:
                stats[table] = 0

        for rel in ["operates_in", "competes_with", "supplies_to", "uses_input",
                     "complement_of", "substitute_for", "uses_technology"]:
            result = await self.db.query(f"SELECT count() AS count FROM {rel} GROUP ALL")
            if result and result[0].get("result"):
                stats[f"rel_{rel}"] = result[0]["result"][0].get("count", 0) if result[0]["result"] else 0
            else:
                stats[f"rel_{rel}"] = 0

        return stats
