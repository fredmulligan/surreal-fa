"""
Pre-built graph queries for common operations.
Used by the shock propagation agent and the query interface.
"""

from src.graph.db import GraphDB, _extract_results


class GraphQueries:
    """Canned queries for the knowledge graph."""

    def __init__(self, db: GraphDB | None = None):
        self.db = db or GraphDB()

    def companies_in_industry(self, industry_name: str) -> list[dict]:
        result = self.db.query("""
            SELECT <-operates_in<-company.* AS companies
            FROM industry WHERE string::lowercase(name) = string::lowercase($name)
        """, {"name": industry_name})
        return _extract_results(result)

    def competitors_of(self, company_name: str) -> list[dict]:
        result = self.db.query("""
            SELECT ->competes_with->company.* AS competitors
            FROM company WHERE string::lowercase(name) = string::lowercase($name)
        """, {"name": company_name})
        return _extract_results(result)

    def supply_chain_of(self, company_name: str) -> dict:
        result = self.db.query("""
            SELECT
                ->supplies_to->company.* AS customers,
                <-supplies_to<-company.* AS suppliers
            FROM company WHERE string::lowercase(name) = string::lowercase($name)
        """, {"name": company_name})
        extracted = _extract_results(result)
        return extracted[0] if extracted else {}

    def commodity_dependents(self, commodity_name: str) -> list[dict]:
        result = self.db.query("""
            SELECT <-uses_input<-company.* AS companies
            FROM commodity WHERE string::lowercase(name) = string::lowercase($name)
        """, {"name": commodity_name})
        return _extract_results(result)

    def shock_cascade(self, event_name: str, depth: int = 3) -> dict:
        cascade = {"event": event_name, "hops": []}

        hop1 = self.db.query("""
            SELECT ->demand_driver->industry.{name, id} AS industries
            FROM event WHERE string::lowercase(name) = string::lowercase($name)
        """, {"name": event_name})
        if hop1:
            cascade["hops"].append({"depth": 1, "type": "industries", "data": _extract_results(hop1)})

        hop2 = self.db.query("""
            SELECT ->demand_driver->industry<-operates_in<-company.{name, ticker, market_cap, id} AS companies
            FROM event WHERE string::lowercase(name) = string::lowercase($name)
        """, {"name": event_name})
        if hop2:
            cascade["hops"].append({"depth": 2, "type": "companies", "data": _extract_results(hop2)})

        hop3 = self.db.query("""
            SELECT
                ->demand_driver->industry<-operates_in<-company->uses_input->commodity.{name, id} AS commodities,
                ->demand_driver->industry<-operates_in<-company->supplies_to->company.{name, ticker, id} AS downstream,
                ->demand_driver->industry<-operates_in<-company->uses_technology->technology.{name, id} AS technologies
            FROM event WHERE string::lowercase(name) = string::lowercase($name)
        """, {"name": event_name})
        if hop3:
            cascade["hops"].append({"depth": 3, "type": "dependencies", "data": _extract_results(hop3)})

        return cascade

    def graph_stats(self) -> dict:
        stats = {}
        for table in ["company", "industry", "technology", "commodity", "policy", "event"]:
            result = self.db.query(f"SELECT count() AS count FROM {table} GROUP ALL")
            extracted = _extract_results(result)
            stats[table] = extracted[0].get("count", 0) if extracted else 0

        for rel in ["operates_in", "competes_with", "supplies_to", "uses_input",
                     "complement_of", "substitute_for", "uses_technology"]:
            result = self.db.query(f"SELECT count() AS count FROM {rel} GROUP ALL")
            extracted = _extract_results(result)
            stats[f"rel_{rel}"] = extracted[0].get("count", 0) if extracted else 0

        return stats
