"""
Graph builder — takes extracted data from connectors and LLM
and writes nodes + relationships to SurrealDB.
"""

from src.graph.db import GraphDB, _clean_id, _extract_results


class GraphBuilder:
    """Builds the knowledge graph in SurrealDB from extracted data."""

    def __init__(self, db: GraphDB | None = None):
        self.db = db or GraphDB()

    # ── Entity Resolution ──

    def resolve_entity(self, table: str, name: str, wikidata_id: str | None = None) -> str | None:
        """Find an existing node by wikidata_id or clean_id. Returns record ID string or None.

        Does NOT create — just looks up. The caller decides whether to create if not found.
        This is the gatekeeper that prevents duplicates across data sources.
        """
        # 1. Check by wikidata_id (canonical identity)
        if wikidata_id:
            result = self.db.query(
                f"SELECT * FROM {table} WHERE wikidata_id = $qid LIMIT 1",
                {"qid": wikidata_id},
            )
            rows = _extract_results(result)
            if rows:
                rid = rows[0]["id"]
                # record_id attribute holds just the ID part
                return str(rid.record_id) if hasattr(rid, "record_id") else str(rid).split(":")[-1]

        # 2. Check by clean_id (name-based)
        clean = _clean_id(name)
        existing = self.db.get_node(table, clean)
        if existing:
            return clean

        return None

    def add_company(self, data: dict) -> str:
        name = data.get("name", "")
        node_id = _clean_id(name)
        self.db.upsert_node("company", node_id, {
            "name": name,
            "ticker": data.get("ticker"),
            "description": data.get("description"),
            # Price
            "current_price": data.get("current_price"),
            "currency": data.get("currency"),
            # Market & revenue
            "market_cap": data.get("market_cap"),
            "revenue": data.get("revenue"),
            # Earnings & valuation
            "earnings": data.get("earnings"),
            "trailing_eps": data.get("trailing_eps"),
            "forward_eps": data.get("forward_eps"),
            "trailing_pe": data.get("trailing_pe"),
            "forward_pe": data.get("forward_pe"),
            "peg_ratio": data.get("peg_ratio"),
            "price_to_book": data.get("price_to_book"),
            "price_to_sales": data.get("price_to_sales"),
            # Margins
            "gross_margin": data.get("gross_margin"),
            "operating_margin": data.get("operating_margin"),
            "profit_margin": data.get("profit_margin"),
            "cost_of_revenue": data.get("cost_of_revenue"),
            # Cash flow & balance sheet
            "ebitda": data.get("ebitda"),
            "free_cash_flow": data.get("free_cash_flow"),
            "operating_cash_flow": data.get("operating_cash_flow"),
            "total_cash": data.get("total_cash"),
            "total_debt": data.get("total_debt"),
            "debt_to_equity": data.get("debt_to_equity"),
            # Growth & risk
            "revenue_growth": data.get("revenue_growth"),
            "earnings_growth": data.get("earnings_growth"),
            "beta": data.get("beta"),
            # Dividends
            "dividend_yield": data.get("dividend_yield"),
            "dividend_rate": data.get("dividend_rate"),
            # Meta
            "employees": data.get("employees"),
            "hq_country": data.get("hq_country"),
            "hq_city": data.get("hq_city"),
            "website": data.get("website"),
            "wikidata_id": data.get("wikidata_id"),
            "yfinance_industry": data.get("yfinance_industry"),
            "yfinance_sector": data.get("yfinance_sector"),
            "founded": data.get("founded"),
            "source": data.get("source", "unknown"),
            "status": data.get("status", "stub"),
        })
        return node_id

    def add_industry(self, name: str, data: dict | None = None) -> str:
        node_id = _clean_id(name)
        props = {"name": name, "source": "agent", "status": "stub"}
        if data:
            props.update(data)
        self.db.upsert_node("industry", node_id, props)
        return node_id

    def add_technology(self, name: str, data: dict | None = None) -> str:
        node_id = _clean_id(name)
        props = {"name": name, "source": "agent"}
        if data:
            props.update(data)
        self.db.upsert_node("technology", node_id, props)
        return node_id

    def add_commodity(self, name: str, data: dict | None = None) -> str:
        node_id = _clean_id(name)
        props = {"name": name, "source": "agent", "status": "stub"}
        if data:
            props.update(data)
        self.db.upsert_node("commodity", node_id, props)
        return node_id

    def add_policy(self, name: str, data: dict | None = None) -> str:
        node_id = _clean_id(name)
        props = {"name": name, "source": "agent"}
        if data:
            props.update(data)
        self.db.upsert_node("policy", node_id, props)
        return node_id

    def add_event(self, name: str, data: dict | None = None) -> str:
        node_id = _clean_id(name)
        props = {"name": name, "source": "agent"}
        if data:
            props.update(data)
        self.db.upsert_node("event", node_id, props)
        return node_id

    def add_product(self, name: str, data: dict | None = None) -> str:
        node_id = _clean_id(name)
        props = {"name": name, "source": "agent"}
        if data:
            props.update(data)
        self.db.upsert_node("product", node_id, props)
        return node_id

    # ── Relationship builders ──

    def link_company_to_industry(self, company, industry, props=None):
        self.db.create_relationship("company", company, "operates_in", "industry", industry, props)

    def link_competitors(self, company_a, company_b, props=None):
        self.db.create_relationship("company", company_a, "competes_with", "company", company_b, props)

    def link_supply_chain(self, supplier, customer, props=None):
        self.db.create_relationship("company", supplier, "supplies_to", "company", customer, props)

    def link_complements(self, company_a, company_b, props=None):
        self.db.create_relationship("company", company_a, "complement_of", "company", company_b, props)

    def link_substitutes(self, company_a, company_b, props=None):
        self.db.create_relationship("company", company_a, "substitute_for", "company", company_b, props)

    def link_subsidiary(self, subsidiary, parent, props=None):
        self.db.create_relationship("company", subsidiary, "subsidiary_of", "company", parent, props)

    def link_uses_technology(self, company, technology, props=None):
        self.db.create_relationship("company", company, "uses_technology", "technology", technology, props)

    def link_investment(self, investor, target, props=None):
        self.db.create_relationship("company", investor, "invested_in", "company", target, props)

    def link_uses_input(self, company, commodity, props=None):
        self.db.create_relationship("company", company, "uses_input", "commodity", commodity, props)

    def link_substitute_inputs(self, commodity_a, commodity_b, props=None):
        self.db.create_relationship("commodity", commodity_a, "substitute_input", "commodity", commodity_b, props)

    def link_event_to_industry(self, event, industry, props=None):
        self.db.create_relationship("event", event, "demand_driver", "industry", industry, props)

    def link_policy_to_company(self, company, policy, props=None):
        self.db.create_relationship("company", company, "affected_by_policy", "policy", policy, props)

    def link_produces(self, company, product, props=None):
        self.db.create_relationship("company", company, "produces", "product", product, props)

    # ── Bulk operations ──

    def enrich_from_yfinance(self, node_id: str, ticker: str) -> bool:
        """Merge yfinance data into an existing stub node. Used when processing queue items."""
        from src.connectors.yfinance_connector import get_company_info, get_key_stats

        info = get_company_info(ticker)
        if not info:
            return False

        stats = get_key_stats(ticker)
        if stats:
            info["gross_margin"] = stats.get("gross_margins")
            info["operating_margin"] = stats.get("operating_margins")
            info["profit_margin"] = stats.get("profit_margins")
            info["cost_of_revenue"] = stats.get("cost_of_revenue")

        # Don't overwrite existing name or wikidata_id
        info.pop("name", None)
        info.pop("source", None)

        industry_name = info.pop("industry", None)
        sector = info.pop("sector", None)

        merge_data = {k: v for k, v in info.items() if v is not None}
        merge_data["source"] = "yfinance"
        if industry_name:
            merge_data["yfinance_industry"] = industry_name
        if sector:
            merge_data["yfinance_sector"] = sector

        self.db.upsert_node("company", node_id, merge_data)
        return True

    def ingest_yfinance_company(self, ticker: str) -> str | None:
        """Pull all data from yfinance for a ticker and write to graph.

        Writes the company node with financials. Does NOT create industry nodes —
        yfinance doesn't know Wikidata Q-IDs, so it can't provide canonical industry
        identity. Instead, stores yfinance_industry as a field on the company for
        Step 2 (Wikidata) to resolve later.
        """
        from src.connectors.yfinance_connector import get_company_info, get_key_stats

        info = get_company_info(ticker)
        if not info or not info.get("name"):
            return None

        stats = get_key_stats(ticker)

        # Merge stats into info, mapping field names to schema
        if stats:
            info["gross_margin"] = stats.get("gross_margins")
            info["operating_margin"] = stats.get("operating_margins")
            info["profit_margin"] = stats.get("profit_margins")
            info["cost_of_revenue"] = stats.get("cost_of_revenue")

        # Store yfinance industry label as field, not as a separate node.
        # Step 2 (Wikidata) creates canonical industry nodes with Q-IDs.
        # If Wikidata has no P452, fallback uses this field to search Wikidata by name.
        industry_name = info.pop("industry", None)
        sector = info.pop("sector", None)
        if industry_name:
            info["yfinance_industry"] = industry_name
        if sector:
            info["yfinance_sector"] = sector

        info["source"] = "yfinance"
        company_id = self.add_company(info)

        return company_id

    def ingest_llm_extraction(self, extraction: dict):
        for company in extraction.get("companies", []):
            if isinstance(company, str):
                company = {"name": company}
            self.add_company(company)

        for industry in extraction.get("industries", []):
            name = industry if isinstance(industry, str) else industry["name"]
            self.add_industry(name, industry if isinstance(industry, dict) else None)

        for tech in extraction.get("technologies", []):
            if isinstance(tech, str):
                tech = {"name": tech}
            self.add_technology(tech["name"], tech)

        for commodity in extraction.get("commodities", []):
            name = commodity if isinstance(commodity, str) else commodity["name"]
            self.add_commodity(name, commodity if isinstance(commodity, dict) else None)

        for policy in extraction.get("policies", []):
            name = policy if isinstance(policy, str) else policy["name"]
            self.add_policy(name, policy if isinstance(policy, dict) else None)

        for rel in extraction.get("relationships", []):
            from_id = rel["from"].lower().replace(" ", "_")
            to_id = rel["to"].lower().replace(" ", "_")
            self.db.create_relationship(
                rel.get("from_type", "company"), from_id,
                rel["rel"],
                rel.get("to_type", "company"), to_id,
                rel.get("properties"),
            )
