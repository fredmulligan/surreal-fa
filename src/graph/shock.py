"""
Shock propagation engine.
This is the product — traces economic shockwaves through the knowledge graph.
"""

import json
from dataclasses import dataclass, field
from src.graph.db import GraphDB, _extract_results


@dataclass
class ShockEffect:
    """A single effect in the shock cascade."""
    entity_type: str
    entity_name: str
    entity_id: str
    effect: str
    direction: str  # positive, negative, mixed
    magnitude: str  # low, medium, high
    hop: int
    path: list[str] = field(default_factory=list)


@dataclass
class ShockCascade:
    """The full cascade from a shock event."""
    shock_description: str
    effects: list[ShockEffect] = field(default_factory=list)

    def by_hop(self) -> dict[int, list[ShockEffect]]:
        grouped = {}
        for e in self.effects:
            grouped.setdefault(e.hop, []).append(e)
        return grouped

    def surprises(self, min_hop: int = 3) -> list[ShockEffect]:
        return [e for e in self.effects if e.hop >= min_hop]

    def to_dict(self) -> dict:
        return {
            "shock": self.shock_description,
            "total_effects": len(self.effects),
            "max_depth": max((e.hop for e in self.effects), default=0),
            "effects_by_hop": {
                hop: [
                    {"entity": e.entity_name, "type": e.entity_type,
                     "effect": e.effect, "direction": e.direction,
                     "magnitude": e.magnitude, "path": e.path}
                    for e in effects
                ]
                for hop, effects in self.by_hop().items()
            },
        }


class ShockEngine:
    """Traces shocks through the knowledge graph."""

    def __init__(self, db: GraphDB | None = None):
        self.db = db or GraphDB()

    def get_directly_affected(self, shock_type: str, shock_target: str) -> list[dict]:
        if shock_type == "commodity":
            result = self.db.query("""
                SELECT <-uses_input<-company.{name, ticker, market_cap, id} AS companies
                FROM commodity WHERE string::lowercase(name) = string::lowercase($name)
            """, {"name": shock_target})
        elif shock_type == "industry":
            result = self.db.query("""
                SELECT <-operates_in<-company.{name, ticker, market_cap, id} AS companies
                FROM industry WHERE string::lowercase(name) = string::lowercase($name)
            """, {"name": shock_target})
        elif shock_type == "company":
            result = self.db.query("""
                SELECT
                    <-supplies_to<-company AS suppliers_affected,
                    ->supplies_to->company AS customers_affected,
                    ->competes_with->company AS competitors,
                    ->complement_of->company AS complements
                FROM company WHERE string::lowercase(name) = string::lowercase($name)
            """, {"name": shock_target})
        elif shock_type == "technology":
            result = self.db.query("""
                SELECT <-uses_technology<-company.{name, ticker, id} AS dependent_companies
                FROM technology WHERE string::lowercase(name) = string::lowercase($name)
            """, {"name": shock_target})
        elif shock_type == "policy":
            result = self.db.query("""
                SELECT <-affected_by_policy<-company.{name, ticker, id} AS affected_companies
                FROM policy WHERE string::lowercase(name) = string::lowercase($name)
            """, {"name": shock_target})
        else:
            return []
        return _extract_results(result)

    def get_second_order(self, company_names: list[str]) -> dict:
        second_order = {"supply_chain": [], "commodities": [], "technologies": []}
        for name in company_names:
            result = self.db.query("""
                SELECT
                    name,
                    ->supplies_to->company.{name, id} AS customers,
                    <-supplies_to<-company.{name, id} AS suppliers,
                    ->uses_input->commodity.{name, id} AS commodity_inputs,
                    ->uses_technology->technology.{name, id} AS technologies,
                    ->complement_of->company.{name, id} AS complements
                FROM company WHERE string::lowercase(name) = string::lowercase($name)
            """, {"name": name})
            for r in _extract_results(result):
                second_order["supply_chain"].extend(r.get("customers", []) or [])
                second_order["supply_chain"].extend(r.get("suppliers", []) or [])
                second_order["commodities"].extend(r.get("commodity_inputs", []) or [])
                second_order["technologies"].extend(r.get("technologies", []) or [])
        return second_order

    def get_commodity_ripple(self, commodity_name: str) -> dict:
        result = self.db.query("""
            SELECT
                <-uses_input<-company.{name, ticker, market_cap} AS companies,
                <-uses_input.{cost_sensitivity, pct_of_costs, criticality} AS edge_props
            FROM commodity WHERE string::lowercase(name) = string::lowercase($name)
        """, {"name": commodity_name})
        return {"commodity": commodity_name, "affected": _extract_results(result)}

    def get_substitute_options(self, commodity_name: str) -> list[dict]:
        result = self.db.query("""
            SELECT ->substitute_input->commodity.{name, id} AS substitutes
            FROM commodity WHERE string::lowercase(name) = string::lowercase($name)
        """, {"name": commodity_name})
        return _extract_results(result)
