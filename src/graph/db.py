"""
SurrealDB client wrapper for Surreal FA.
Handles connection, node creation, and relationship creation.

Uses the blocking SurrealDB SDK (surrealdb 1.x).
Surreal() connects on init — no separate connect() call needed.
"""

import os
import json
import threading
from dotenv import load_dotenv
from surrealdb import Surreal

load_dotenv()

SURREAL_URL = os.getenv("SURREAL_URL", "ws://localhost:8000/rpc")
SURREAL_TOKEN = os.getenv("SURREAL_TOKEN", "")
SURREAL_USER = os.getenv("SURREAL_USER", "root")
SURREAL_PASS = os.getenv("SURREAL_PASS", "root")
SURREAL_NS = os.getenv("SURREAL_NAMESPACE", "surreal_fa")
SURREAL_DB = os.getenv("SURREAL_DATABASE", "surreal_fa")


class GraphDB:
    """Thread-safe blocking SurrealDB client for the knowledge graph.
    Each thread gets its own connection via thread-local storage."""

    def __init__(self):
        self._local = threading.local()

    def _get_conn(self) -> Surreal:
        """Get or create a thread-local connection."""
        if not hasattr(self._local, "db") or self._local.db is None:
            db = Surreal(SURREAL_URL)
            if SURREAL_TOKEN:
                db.authenticate(SURREAL_TOKEN)
            else:
                db.signin({"username": SURREAL_USER, "password": SURREAL_PASS})
            db.use(SURREAL_NS, SURREAL_DB)
            self._local.db = db
        return self._local.db

    def connect(self):
        """Ensure connection exists for current thread."""
        self._get_conn()

    def close(self):
        if hasattr(self._local, "db") and self._local.db:
            try:
                self._local.db.close()
            except Exception:
                pass  # HTTP connections don't implement close
            self._local.db = None

    def query(self, sql: str, vars: dict | None = None):
        """Run a raw SurrealQL query."""
        conn = self._get_conn()
        sql = sql.strip()
        if not sql.endswith(";"):
            sql += ";"
        return conn.query(sql, vars or {})

    # ── Node operations ──

    def upsert_node(self, table: str, node_id: str, data: dict) -> dict:
        """
        Create or update a node. node_id becomes the record ID.
        e.g. upsert_node("company", "tesla", {"name": "Tesla", ...})
        creates company:tesla
        """
        clean_id = _clean_id(node_id)
        clean_data = {k: v for k, v in data.items() if v is not None}
        return self.query(
            f"UPSERT {table}:{clean_id} MERGE $data",
            {"data": clean_data},
        )

    def get_node(self, table: str, node_id: str) -> dict | None:
        """Get a node by table and ID."""
        clean_id = _clean_id(node_id)
        result = self.query(f"SELECT * FROM {table}:{clean_id}")
        extracted = _extract_results(result)
        return extracted[0] if extracted else None

    def find_node(self, table: str, name: str) -> dict | None:
        """Find a node by name field."""
        result = self.query(
            f"SELECT * FROM {table} WHERE name = $name LIMIT 1",
            {"name": name},
        )
        extracted = _extract_results(result)
        return extracted[0] if extracted else None

    def list_nodes(self, table: str, limit: int = 100) -> list[dict]:
        """List all nodes of a given type."""
        result = self.query(f"SELECT * FROM {table} LIMIT {limit}")
        return _extract_results(result)

    # ── Relationship operations ──

    def create_relationship(
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
        clean_from = _clean_id(from_id)
        clean_to = _clean_id(to_id)

        if properties:
            return self.query(
                f"RELATE {from_table}:{clean_from}->{rel_type}->{to_table}:{clean_to} SET {_dict_to_set(properties)}"
            )
        else:
            return self.query(
                f"RELATE {from_table}:{clean_from}->{rel_type}->{to_table}:{clean_to}"
            )

    def get_relationships(
        self, table: str, node_id: str, rel_type: str, direction: str = "out"
    ) -> list[dict]:
        """
        Get relationships for a node.
        direction: "out" (node->rel->?), "in" (?->rel->node), "both"
        """
        clean_id = _clean_id(node_id)

        if direction == "out":
            q = f"SELECT ->{rel_type}->? AS targets FROM {table}:{clean_id}"
        elif direction == "in":
            q = f"SELECT <-{rel_type}<-? AS sources FROM {table}:{clean_id}"
        else:
            q = f"SELECT ->{rel_type}->? AS out_targets, <-{rel_type}<-? AS in_sources FROM {table}:{clean_id}"

        return _extract_results(self.query(q))

    # ── Graph traversal (for shock propagation) ──

    def traverse(self, start_table: str, start_id: str, depth: int = 3) -> list[dict]:
        """
        Traverse the graph from a starting node up to N hops.
        Returns all connected nodes and the paths to reach them.
        """
        clean_id = _clean_id(start_id)
        result = self.query(f"""
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
        return _extract_results(result)

    def shock_propagate(self, event_name: str) -> list[dict]:
        """
        Trace shock propagation from an event through the graph.
        Returns the cascade path.
        """
        result = self.query("""
            SELECT
                *,
                ->demand_driver->industry AS affected_industries,
                ->demand_driver->industry<-operates_in<-company AS affected_companies,
                ->demand_driver->industry<-operates_in<-company->uses_input->commodity AS affected_commodities,
                ->demand_driver->industry<-operates_in<-company->supplies_to->company AS downstream_companies
            FROM event WHERE name = $name
        """, {"name": event_name})
        return _extract_results(result)

    def get_full_graph(self, limit: int = 500) -> dict:
        """Get all nodes and edges for visualization."""
        nodes = {}
        for table in ["company", "industry", "technology", "commodity", "policy", "event", "product"]:
            result = self.query(f"SELECT * FROM {table} LIMIT {limit}")
            extracted = _extract_results(result)
            if extracted:
                nodes[table] = extracted

        edges = {}
        for rel in ["operates_in", "competes_with", "supplies_to", "complement_of",
                     "substitute_for", "subsidiary_of", "uses_technology", "invested_in",
                     "uses_input", "substitute_input", "demand_driver", "affected_by_policy", "produces"]:
            result = self.query(f"SELECT * FROM {rel} LIMIT {limit}")
            extracted = _extract_results(result)
            if extracted:
                edges[rel] = extracted

        return {"nodes": nodes, "edges": edges}


def _extract_results(result) -> list[dict]:
    """Extract results from SurrealDB query response (handles SDK format variations).
    HTTP SDK returns flat list of dicts. WS SDK may wrap in {"result": [...]}.
    """
    if not result:
        return []
    if isinstance(result, list):
        if not result:
            return []
        first = result[0]
        # WS SDK format: [{"result": [...], "status": "OK"}]
        if isinstance(first, dict) and "result" in first and "status" in first:
            return first["result"] or []
        # HTTP SDK format: flat list of dicts
        if isinstance(first, dict):
            return result
        # Nested list
        if isinstance(first, list):
            return first
    if isinstance(result, dict):
        return [result]
    return []


def _clean_id(raw: str) -> str:
    """Clean a string for use as a SurrealDB record ID.
    Strips non-ASCII chars (Citroën → citroen) and normalizes."""
    import unicodedata
    # Decompose accented chars (ë → e + combining diaeresis), then strip combining marks
    nfkd = unicodedata.normalize('NFKD', raw)
    ascii_only = ''.join(c for c in nfkd if not unicodedata.combining(c) and ord(c) < 128)
    return (ascii_only.lower()
            .replace(" ", "_").replace("-", "_")
            .replace(".", "").replace(",", "")
            .replace("'", "").replace('"', "")
            .replace("(", "").replace(")", "")
            .replace("/", "_").replace("&", "and")
            .replace("+", "and").replace("@", "at")
            .replace("#", "").replace("!", "")
            .replace("?", "").replace("*", "")
            .replace("[", "").replace("]", "")
            .replace("{", "").replace("}", "")
            .replace(":", "").replace(";", "")
            .replace("~", "").replace("`", "")
            .replace("$", "").replace("%", "")
            .replace("^", "").replace("|", "")
            .replace("<", "").replace(">", "")
            .replace("=", ""))


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
            parts.append(f"{k} = {json.dumps(v)}")
    return ", ".join(parts)
