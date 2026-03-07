"""
SurrealDB client wrapper for Surreal FA.
Handles connection, node creation, and relationship creation.
"""

import os
import asyncio
from surrealdb import Surreal

SURREAL_URL = os.getenv("SURREAL_URL", "ws://localhost:8000/rpc")
SURREAL_USER = os.getenv("SURREAL_USER", "root")
SURREAL_PASS = os.getenv("SURREAL_PASS", "root")
SURREAL_NS = os.getenv("SURREAL_NAMESPACE", "surreal_fa")
SURREAL_DB = os.getenv("SURREAL_DATABASE", "surreal_fa")


class GraphDB:
    """Async SurrealDB client for the knowledge graph."""

    def __init__(self):
        self.db = Surreal(SURREAL_URL)
        self._connected = False

    async def connect(self):
        if self._connected:
            return
        await self.db.connect()
        await self.db.signin({"username": SURREAL_USER, "password": SURREAL_PASS})
        await self.db.use(SURREAL_NS, SURREAL_DB)
        self._connected = True

    async def close(self):
        if self._connected:
            await self.db.close()
            self._connected = False

    async def query(self, sql: str, vars: dict | None = None):
        """Run a raw SurrealQL query."""
        await self.connect()
        return await self.db.query(sql, vars or {})

    # ── Node operations ──

    async def upsert_node(self, table: str, node_id: str, data: dict) -> dict:
        """
        Create or update a node. node_id becomes the record ID.
        e.g. upsert_node("company", "tesla", {"name": "Tesla", ...})
        creates company:tesla
        """
        await self.connect()
        # Clean the ID for SurrealDB (lowercase, no spaces, alphanumeric + underscore)
        clean_id = _clean_id(node_id)
        # Merge to upsert
        result = await self.db.query(
            f"UPDATE {table}:{clean_id} MERGE $data",
            {"data": data},
        )
        return result

    async def get_node(self, table: str, node_id: str) -> dict | None:
        """Get a node by table and ID."""
        await self.connect()
        clean_id = _clean_id(node_id)
        result = await self.db.query(f"SELECT * FROM {table}:{clean_id}")
        if result and result[0].get("result"):
            return result[0]["result"][0] if result[0]["result"] else None
        return None

    async def find_node(self, table: str, name: str) -> dict | None:
        """Find a node by name field."""
        await self.connect()
        result = await self.db.query(
            f"SELECT * FROM {table} WHERE name = $name LIMIT 1",
            {"name": name},
        )
        if result and result[0].get("result"):
            return result[0]["result"][0] if result[0]["result"] else None
        return None

    async def list_nodes(self, table: str, limit: int = 100) -> list[dict]:
        """List all nodes of a given type."""
        await self.connect()
        result = await self.db.query(f"SELECT * FROM {table} LIMIT {limit}")
        if result and result[0].get("result"):
            return result[0]["result"]
        return []

    # ── Relationship operations ──

    async def create_relationship(
        self,
        from_table: str,
        from_id: str,
        rel_type: str,
        to_table: str,
        to_id: str,
        properties: dict | None = None,
    ) -> dict:
        """
        Create a relationship (edge) between two nodes.
        e.g. create_relationship("company", "tesla", "operates_in", "industry", "electric_vehicles")
        """
        await self.connect()
        clean_from = _clean_id(from_id)
        clean_to = _clean_id(to_id)

        if properties:
            result = await self.db.query(
                f"RELATE {from_table}:{clean_from}->{rel_type}->{to_table}:{clean_to} SET {_dict_to_set(properties)}"
            )
        else:
            result = await self.db.query(
                f"RELATE {from_table}:{clean_from}->{rel_type}->{to_table}:{clean_to}"
            )
        return result

    async def get_relationships(
        self, table: str, node_id: str, rel_type: str, direction: str = "out"
    ) -> list[dict]:
        """
        Get relationships for a node.
        direction: "out" (node->rel->?), "in" (?->rel->node), "both"
        """
        await self.connect()
        clean_id = _clean_id(node_id)

        if direction == "out":
            q = f"SELECT ->{rel_type}->? AS targets FROM {table}:{clean_id}"
        elif direction == "in":
            q = f"SELECT <-{rel_type}<-? AS sources FROM {table}:{clean_id}"
        else:
            q = f"SELECT ->{rel_type}->? AS out_targets, <-{rel_type}<-? AS in_sources FROM {table}:{clean_id}"

        result = await self.db.query(q)
        if result and result[0].get("result"):
            return result[0]["result"]
        return []

    # ── Graph traversal (for shock propagation) ──

    async def traverse(self, start_table: str, start_id: str, depth: int = 3) -> list[dict]:
        """
        Traverse the graph from a starting node up to N hops.
        Returns all connected nodes and the paths to reach them.
        """
        await self.connect()
        clean_id = _clean_id(start_id)
        # Get the ego graph — all outgoing relationships
        result = await self.db.query(f"""
            SELECT
                *,
                ->operates_in->industry AS industries,
                ->competes_with->company AS competitors,
                ->supplies_to->company AS customers,
                <-supplies_to<-company AS suppliers,
                ->complement_of->company AS complements,
                ->substitute_for->company AS substitutes,
                ->uses_input->commodity AS inputs,
                ->uses_technology->technology AS technologies,
                ->affected_by_policy->policy AS policies,
                ->subsidiary_of->company AS parent_companies,
                <-subsidiary_of<-company AS subsidiaries,
                ->invested_in->company AS investments
            FROM {start_table}:{clean_id}
        """)
        if result and result[0].get("result"):
            return result[0]["result"]
        return []

    async def shock_propagate(self, event_name: str) -> list[dict]:
        """
        Trace shock propagation from an event through the graph.
        Returns the cascade path.
        """
        await self.connect()
        # 3-hop traversal: event → industries → companies → their dependencies
        result = await self.db.query("""
            SELECT
                *,
                ->demand_driver->industry AS affected_industries,
                ->demand_driver->industry<-operates_in<-company AS affected_companies,
                ->demand_driver->industry<-operates_in<-company->uses_input->commodity AS affected_commodities,
                ->demand_driver->industry<-operates_in<-company->supplies_to->company AS downstream_companies
            FROM event WHERE name = $name
        """, {"name": event_name})
        if result and result[0].get("result"):
            return result[0]["result"]
        return []

    async def get_full_graph(self, limit: int = 500) -> dict:
        """Get all nodes and edges for visualization."""
        await self.connect()
        nodes = {}
        for table in ["company", "industry", "technology", "commodity", "policy", "event", "product"]:
            result = await self.db.query(f"SELECT * FROM {table} LIMIT {limit}")
            if result and result[0].get("result"):
                nodes[table] = result[0]["result"]

        edges = {}
        for rel in ["operates_in", "competes_with", "supplies_to", "complement_of",
                     "substitute_for", "subsidiary_of", "uses_technology", "invested_in",
                     "uses_input", "substitute_input", "demand_driver", "affected_by_policy", "produces"]:
            result = await self.db.query(f"SELECT * FROM {rel} LIMIT {limit}")
            if result and result[0].get("result"):
                edges[rel] = result[0]["result"]

        return {"nodes": nodes, "edges": edges}


def _clean_id(raw: str) -> str:
    """Clean a string for use as a SurrealDB record ID."""
    return raw.lower().replace(" ", "_").replace("-", "_").replace(".", "").replace(",", "").replace("'", "").replace('"', "").replace("(", "").replace(")", "").replace("/", "_").replace("&", "and")


def _dict_to_set(d: dict) -> str:
    """Convert a dict to SurrealQL SET clause."""
    parts = []
    for k, v in d.items():
        if v is None:
            continue
        if isinstance(v, str):
            parts.append(f'{k} = "{v}"')
        elif isinstance(v, bool):
            parts.append(f"{k} = {'true' if v else 'false'}")
        elif isinstance(v, (int, float)):
            parts.append(f"{k} = {v}")
        elif isinstance(v, list):
            import json
            parts.append(f"{k} = {json.dumps(v)}")
    return ", ".join(parts)


# Convenience: run async functions from sync context
def run_sync(coro):
    """Run an async function synchronously."""
    try:
        loop = asyncio.get_running_loop()
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return loop.run_in_executor(pool, asyncio.run, coro)
    except RuntimeError:
        return asyncio.run(coro)
