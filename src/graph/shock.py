"""
Shock propagation engine.
This is the product — traces economic shockwaves through the knowledge graph.
"""

from dataclasses import dataclass, field
from src.graph.db import GraphDB


@dataclass
class ShockEffect:
    """A single effect in the shock cascade."""
    entity_type: str  # company, industry, commodity, etc.
    entity_name: str
    entity_id: str
    effect: str  # description of the effect
    direction: str  # positive, negative, mixed
    magnitude: str  # low, medium, high
    hop: int  # how many hops from the shock source
    path: list[str] = field(default_factory=list)  # the chain of reasoning


@dataclass
class ShockCascade:
    """The full cascade from a shock event."""
    shock_description: str
    effects: list[ShockEffect] = field(default_factory=list)

    def by_hop(self) -> dict[int, list[ShockEffect]]:
        """Group effects by hop distance."""
        grouped = {}
        for e in self.effects:
            grouped.setdefault(e.hop, []).append(e)
        return grouped

    def surprises(self, min_hop: int = 3) -> list[ShockEffect]:
        """Get the surprising effects — the ones far from the epicenter."""
        return [e for e in self.effects if e.hop >= min_hop]

    def to_dict(self) -> dict:
        return {
            "shock": self.shock_description,
            "total_effects": len(self.effects),
            "max_depth": max((e.hop for e in self.effects), default=0),
            "effects_by_hop": {
                hop: [
                    {
                        "entity": e.entity_name,
                        "type": e.entity_type,
                        "effect": e.effect,
                        "direction": e.direction,
                        "magnitude": e.magnitude,
                        "path": e.path,
                    }
                    for e in effects
                ]
                for hop, effects in self.by_hop().items()
            },
        }


class ShockEngine:
    """
    Traces shocks through the knowledge graph.

    The engine does graph traversal; the LLM agent provides the reasoning
    about what each hop means (how does a copper price increase affect
    a toy manufacturer?).

    Typical flow:
    1. LLM identifies the initial shock and affected industries/commodities
    2. Engine traverses the graph to find connected entities
    3. LLM reasons about the effect at each hop
    4. Engine records the cascade
    """

    def __init__(self, db: GraphDB | None = None):
        self.db = db or GraphDB()

    async def get_directly_affected(self, shock_type: str, shock_target: str) -> list[dict]:
        """
        Get entities directly affected by a shock.
        shock_type: "commodity", "industry", "company", "policy", "technology"
        shock_target: name of the affected thing
        """
        if shock_type == "commodity":
            # Who uses this commodity?
            result = await self.db.query("""
                SELECT
                    <-uses_input<-company.{name, ticker, market_cap, id} AS companies,
                    <-uses_input.{cost_sensitivity, pct_of_costs} AS edge_data
                FROM commodity WHERE name = $name
            """, {"name": shock_target})
        elif shock_type == "industry":
            result = await self.db.query("""
                SELECT
                    <-operates_in<-company.{name, ticker, market_cap, id} AS companies
                FROM industry WHERE name = $name
            """, {"name": shock_target})
        elif shock_type == "company":
            # Who depends on this company (supply chain)?
            result = await self.db.query("""
                SELECT
                    <-supplies_to<-company AS suppliers_affected,
                    ->supplies_to->company AS customers_affected,
                    ->competes_with->company AS competitors,
                    ->complement_of->company AS complements
                FROM company WHERE name = $name
            """, {"name": shock_target})
        elif shock_type == "technology":
            result = await self.db.query("""
                SELECT
                    <-uses_technology<-company.{name, ticker, id} AS dependent_companies
                FROM technology WHERE name = $name
            """, {"name": shock_target})
        elif shock_type == "policy":
            result = await self.db.query("""
                SELECT
                    <-affected_by_policy<-company.{name, ticker, id} AS affected_companies
                FROM policy WHERE name = $name
            """, {"name": shock_target})
        else:
            return []

        if result and result[0].get("result"):
            return result[0]["result"]
        return []

    async def get_second_order(self, company_names: list[str]) -> dict:
        """
        For a list of affected companies, find what they depend on
        and what depends on them — the second-order effects.
        """
        second_order = {"supply_chain": [], "commodities": [], "technologies": []}

        for name in company_names:
            result = await self.db.query("""
                SELECT
                    name,
                    ->supplies_to->company.{name, id} AS customers,
                    <-supplies_to<-company.{name, id} AS suppliers,
                    ->uses_input->commodity.{name, id} AS commodity_inputs,
                    ->uses_technology->technology.{name, id} AS technologies,
                    ->complement_of->company.{name, id} AS complements
                FROM company WHERE name = $name
            """, {"name": name})
            if result and result[0].get("result"):
                for r in result[0]["result"]:
                    second_order["supply_chain"].extend(r.get("customers", []) or [])
                    second_order["supply_chain"].extend(r.get("suppliers", []) or [])
                    second_order["commodities"].extend(r.get("commodity_inputs", []) or [])
                    second_order["technologies"].extend(r.get("technologies", []) or [])

        return second_order

    async def get_commodity_ripple(self, commodity_name: str) -> dict:
        """
        When a commodity price changes, who's affected?
        Returns companies grouped by cost sensitivity.
        """
        result = await self.db.query("""
            SELECT
                in AS company,
                cost_sensitivity,
                pct_of_costs
            FROM uses_input
            WHERE out = (SELECT id FROM commodity WHERE name = $name LIMIT 1)
            ORDER BY cost_sensitivity DESC
        """, {"name": commodity_name})

        if result and result[0].get("result"):
            return {
                "commodity": commodity_name,
                "affected": result[0]["result"],
            }
        return {"commodity": commodity_name, "affected": []}

    async def get_substitute_options(self, commodity_name: str) -> list[dict]:
        """Find substitute commodities/inputs."""
        result = await self.db.query("""
            SELECT
                ->substitute_input->commodity.{name, id} AS substitutes,
                ->substitute_input.{feasibility, cost_premium} AS sub_details
            FROM commodity WHERE name = $name
        """, {"name": commodity_name})
        if result and result[0].get("result"):
            return result[0]["result"]
        return []
