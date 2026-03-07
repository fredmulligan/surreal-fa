"""
Graph builder — takes extracted data from connectors and LLM
and writes nodes + relationships to SurrealDB.
"""

from src.graph.db import GraphDB


class GraphBuilder:
    """Builds the knowledge graph in SurrealDB from extracted data."""

    def __init__(self, db: GraphDB | None = None):
        self.db = db or GraphDB()

    async def add_company(self, data: dict) -> str:
        """
        Add a company node. Returns the node ID.
        data should have: name, ticker, description, market_cap, etc.
        """
        name = data.get("name", "")
        node_id = name.lower().replace(" ", "_")
        await self.db.upsert_node("company", node_id, {
            "name": name,
            "ticker": data.get("ticker"),
            "description": data.get("description"),
            "market_cap": data.get("market_cap"),
            "revenue": data.get("revenue"),
            "employees": data.get("employees"),
            "hq_country": data.get("hq_country"),
            "hq_city": data.get("hq_city"),
            "website": data.get("website"),
            "wikidata_id": data.get("wikidata_id"),
            "founded": data.get("founded"),
            "source": data.get("source", "unknown"),
        })
        return node_id

    async def add_industry(self, name: str, data: dict | None = None) -> str:
        """Add an industry node."""
        node_id = name.lower().replace(" ", "_")
        props = {"name": name, "source": "agent"}
        if data:
            props.update(data)
        await self.db.upsert_node("industry", node_id, props)
        return node_id

    async def add_technology(self, name: str, data: dict | None = None) -> str:
        """Add a technology node."""
        node_id = name.lower().replace(" ", "_")
        props = {"name": name, "source": "agent"}
        if data:
            props.update(data)
        await self.db.upsert_node("technology", node_id, props)
        return node_id

    async def add_commodity(self, name: str, data: dict | None = None) -> str:
        """Add a commodity node."""
        node_id = name.lower().replace(" ", "_")
        props = {"name": name, "source": "agent"}
        if data:
            props.update(data)
        await self.db.upsert_node("commodity", node_id, props)
        return node_id

    async def add_policy(self, name: str, data: dict | None = None) -> str:
        """Add a policy/subsidy node."""
        node_id = name.lower().replace(" ", "_")
        props = {"name": name, "source": "agent"}
        if data:
            props.update(data)
        await self.db.upsert_node("policy", node_id, props)
        return node_id

    async def add_event(self, name: str, data: dict | None = None) -> str:
        """Add an event/shock node."""
        node_id = name.lower().replace(" ", "_")
        props = {"name": name, "source": "agent"}
        if data:
            props.update(data)
        await self.db.upsert_node("event", node_id, props)
        return node_id

    async def add_product(self, name: str, data: dict | None = None) -> str:
        """Add a product node."""
        node_id = name.lower().replace(" ", "_")
        props = {"name": name, "source": "agent"}
        if data:
            props.update(data)
        await self.db.upsert_node("product", node_id, props)
        return node_id

    # ── Relationship builders ──

    async def link_company_to_industry(self, company: str, industry: str, props: dict | None = None):
        """Company OPERATES_IN industry."""
        await self.db.create_relationship("company", company, "operates_in", "industry", industry, props)

    async def link_competitors(self, company_a: str, company_b: str, props: dict | None = None):
        """Company COMPETES_WITH company (bidirectional)."""
        await self.db.create_relationship("company", company_a, "competes_with", "company", company_b, props)

    async def link_supply_chain(self, supplier: str, customer: str, props: dict | None = None):
        """Supplier SUPPLIES_TO customer."""
        await self.db.create_relationship("company", supplier, "supplies_to", "company", customer, props)

    async def link_complements(self, company_a: str, company_b: str, props: dict | None = None):
        """Company COMPLEMENT_OF company."""
        await self.db.create_relationship("company", company_a, "complement_of", "company", company_b, props)

    async def link_substitutes(self, company_a: str, company_b: str, props: dict | None = None):
        """Company SUBSTITUTE_FOR company."""
        await self.db.create_relationship("company", company_a, "substitute_for", "company", company_b, props)

    async def link_subsidiary(self, subsidiary: str, parent: str, props: dict | None = None):
        """Subsidiary SUBSIDIARY_OF parent."""
        await self.db.create_relationship("company", subsidiary, "subsidiary_of", "company", parent, props)

    async def link_uses_technology(self, company: str, technology: str, props: dict | None = None):
        """Company USES_TECHNOLOGY technology."""
        await self.db.create_relationship("company", company, "uses_technology", "technology", technology, props)

    async def link_investment(self, investor: str, target: str, props: dict | None = None):
        """Investor INVESTED_IN target."""
        await self.db.create_relationship("company", investor, "invested_in", "company", target, props)

    async def link_uses_input(self, company: str, commodity: str, props: dict | None = None):
        """Company USES_INPUT commodity."""
        await self.db.create_relationship("company", company, "uses_input", "commodity", commodity, props)

    async def link_substitute_inputs(self, commodity_a: str, commodity_b: str, props: dict | None = None):
        """Commodity SUBSTITUTE_INPUT commodity."""
        await self.db.create_relationship("commodity", commodity_a, "substitute_input", "commodity", commodity_b, props)

    async def link_event_to_industry(self, event: str, industry: str, props: dict | None = None):
        """Event DEMAND_DRIVER industry."""
        await self.db.create_relationship("event", event, "demand_driver", "industry", industry, props)

    async def link_policy_to_company(self, company: str, policy: str, props: dict | None = None):
        """Company AFFECTED_BY_POLICY policy."""
        await self.db.create_relationship("company", company, "affected_by_policy", "policy", policy, props)

    async def link_produces(self, company: str, product: str, props: dict | None = None):
        """Company PRODUCES product."""
        await self.db.create_relationship("company", company, "produces", "product", product, props)

    # ── Bulk operations ──

    async def ingest_yfinance_company(self, yf_data: dict) -> str | None:
        """
        Take yfinance company data, create company + industry nodes and link them.
        """
        if not yf_data:
            return None

        company_id = await self.add_company(yf_data)

        # Create industry node and link
        industry_name = yf_data.get("industry")
        if industry_name:
            industry_id = await self.add_industry(industry_name, {
                "sector": yf_data.get("sector"),
            })
            await self.link_company_to_industry(company_id, industry_id)

        return company_id

    async def ingest_llm_extraction(self, extraction: dict):
        """
        Take LLM-extracted entities and relationships and add them to the graph.
        Expected format:
        {
            "companies": [{"name": ..., "description": ...}, ...],
            "industries": ["name", ...],
            "technologies": [{"name": ..., "maturity": ...}, ...],
            "commodities": ["name", ...],
            "relationships": [
                {"from": "Tesla", "from_type": "company", "rel": "competes_with",
                 "to": "Rivian", "to_type": "company", "properties": {...}},
                ...
            ]
        }
        """
        node_ids = {}

        # Create nodes
        for company in extraction.get("companies", []):
            if isinstance(company, str):
                company = {"name": company}
            nid = await self.add_company(company)
            node_ids[company["name"]] = ("company", nid)

        for industry in extraction.get("industries", []):
            if isinstance(industry, str):
                industry = {"name": industry}
            name = industry if isinstance(industry, str) else industry["name"]
            nid = await self.add_industry(name, industry if isinstance(industry, dict) else None)
            node_ids[name] = ("industry", nid)

        for tech in extraction.get("technologies", []):
            if isinstance(tech, str):
                tech = {"name": tech}
            nid = await self.add_technology(tech["name"], tech)
            node_ids[tech["name"]] = ("technology", nid)

        for commodity in extraction.get("commodities", []):
            if isinstance(commodity, str):
                commodity = {"name": commodity}
            name = commodity if isinstance(commodity, str) else commodity["name"]
            nid = await self.add_commodity(name, commodity if isinstance(commodity, dict) else None)
            node_ids[name] = ("commodity", nid)

        for policy in extraction.get("policies", []):
            if isinstance(policy, str):
                policy = {"name": policy}
            name = policy if isinstance(policy, str) else policy["name"]
            nid = await self.add_policy(name, policy if isinstance(policy, dict) else None)
            node_ids[name] = ("policy", nid)

        # Create relationships
        for rel in extraction.get("relationships", []):
            from_type = rel.get("from_type", "company")
            to_type = rel.get("to_type", "company")
            from_id = rel["from"].lower().replace(" ", "_")
            to_id = rel["to"].lower().replace(" ", "_")
            rel_type = rel["rel"]
            props = rel.get("properties", {})

            await self.db.create_relationship(from_type, from_id, rel_type, to_type, to_id, props)
