"""
Surreal FA — Graph query tools.

Each tool is a fixed SurrealQL query with parameters.
The LLM picks the tool and fills in the parameters.
Nothing is generated — the queries are predetermined.
"""

import json
from langchain_core.tools import tool

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.graph.db import GraphDB

db = GraphDB()


def _rid_to_str(val):
    """Convert RecordID to just the record key (no table prefix)."""
    if val is None:
        return None
    if hasattr(val, 'id'):
        return str(val.id)
    s = str(val)
    return s.split(":", 1)[1] if ":" in s else s


def _resolve_industry(raw: str) -> str | None:
    """Resolve a user-provided industry name to its actual SurrealDB record ID.
    Tries exact ID first, then name search. Prefers shortest name match (closest to query)."""
    clean = raw.lower().replace(" ", "_").replace("-", "_")
    # Try exact ID
    hit = db.query(f"SELECT id FROM industry:{clean}")
    if hit:
        return clean
    # Search by name — get candidates, pick best match (shortest name = closest)
    term = raw.lower().replace("_", " ")
    rows = db.query(
        "SELECT id, name FROM industry WHERE string::lowercase(name) CONTAINS string::lowercase($term) LIMIT 20",
        {"term": term}
    )
    if not rows:
        return None
    # Prefer exact name match, then shortest name (most specific)
    for row in rows:
        if row.get("name", "").lower() == term:
            rid = row["id"]
            return str(rid.id) if hasattr(rid, 'id') else str(rid).split(":", 1)[-1]
    best = min(rows, key=lambda r: len(r.get("name", "") or ""))
    rid = best["id"]
    return str(rid.id) if hasattr(rid, 'id') else str(rid).split(":", 1)[-1]


def _resolve_industries(raw: str) -> list[tuple[str, str]]:
    """Resolve a user-provided term to ALL matching industries.
    Returns list of (id, name) tuples. For ambiguous terms like 'battery',
    returns all battery-related industries."""
    clean = raw.lower().replace(" ", "_").replace("-", "_")
    # Try exact ID first — if it hits, that's the one they meant
    hit = db.query(f"SELECT id, name FROM industry:{clean}")
    if hit:
        name = hit[0].get("name", clean) if hit else clean
        return [(clean, name)]
    # Search by name — return ALL matches
    term = raw.lower().replace("_", " ")
    rows = db.query(
        "SELECT id, name FROM industry WHERE string::lowercase(name) CONTAINS string::lowercase($term) LIMIT 50",
        {"term": term}
    )
    if not rows:
        return []
    results = []
    for row in rows:
        rid = row["id"]
        rid_str = str(rid.id) if hasattr(rid, 'id') else str(rid).split(":", 1)[-1]
        results.append((rid_str, row.get("name", rid_str)))
    return results


def _get_inputs(industry_id: str) -> tuple[str | None, list[dict]]:
    """Get direct inputs for an industry. Returns (industry_name, list of input dicts)."""
    rows = db.query(f"""
        SELECT
            in.id AS from_id,
            in.name AS from_name,
            out.id AS to_id,
            out.name AS to_name
        FROM industry_uses_input
        WHERE in = industry:{industry_id}
    """)
    if not rows:
        return None, []
    name = rows[0].get("from_name", industry_id)
    inputs = [{"id": _rid_to_str(r.get("to_id")), "name": r.get("to_name")} for r in rows]
    return name, inputs


@tool
def supply_chain_inputs(industry: str, depth: int = 1) -> str:
    """Get what goes into an industry — its direct inputs/raw materials.

    Use this when the user asks things like:
    - "What goes into steel?"
    - "What are the inputs to solar panels?"
    - "What does copper need?"

    If the term is ambiguous, returns inputs across ALL matching industries.

    Args:
        industry: lowercase with underscores: steel, solar_panel, copper.
        depth: 1 for direct inputs only (default), 2 to also show what goes into each input.
    """
    matches = _resolve_industries(industry)

    if not matches:
        return json.dumps({
            "tool": "supply_chain_inputs",
            "industry": industry,
            "depth": depth,
            "inputs": [],
            "edges": [],
            "message": f"Industry '{industry}' not found in the graph."
        })

    all_nodes = {}
    edges = []
    center_ids = set()

    for ind_id, ind_name in matches:
        center_ids.add(ind_id)
        all_nodes[ind_id] = ind_name
        _, inputs = _get_inputs(ind_id)
        for inp in inputs:
            all_nodes[inp["id"]] = inp["name"]
            edges.append({"from_id": inp["id"], "from_name": inp["name"],
                          "to_id": ind_id, "to_name": ind_name})

            if depth >= 2:
                inp_id = inp["id"]
                if not inp_id:
                    continue
                while ":" in inp_id:
                    inp_id = inp_id.split(":", 1)[1]
                _, sub_inputs = _get_inputs(inp_id)
                for sub in sub_inputs:
                    edges.append({"from_id": sub["id"], "from_name": sub["name"],
                                  "to_id": inp["id"], "to_name": inp["name"]})
                    all_nodes[sub["id"]] = sub["name"]

    non_center = [{"id": k, "name": v} for k, v in all_nodes.items() if k not in center_ids]

    if not non_center:
        names = ", ".join(n for _, n in matches)
        return json.dumps({
            "tool": "supply_chain_inputs",
            "industry": industry,
            "depth": depth,
            "inputs": [],
            "edges": [],
            "message": f"No inputs found for '{names}'."
        })

    if len(matches) == 1:
        industry_name = matches[0][1]
        resolved = matches[0][0]
    else:
        industry_name = f"{industry} ({len(matches)} industries)"
        resolved = industry

    return json.dumps({
        "tool": "supply_chain_inputs",
        "industry": resolved,
        "industry_name": industry_name,
        "depth": depth,
        "center_ids": [{"id": i, "name": n} for i, n in matches],
        "inputs": non_center,
        "edges": edges,
    })


def _get_dependents(industry_id: str) -> tuple[str | None, list[dict]]:
    """Get industries that depend on this industry (reverse edges)."""
    rows = db.query(f"""
        SELECT
            in.id AS from_id,
            in.name AS from_name,
            out.id AS to_id,
            out.name AS to_name
        FROM industry_uses_input
        WHERE out = industry:{industry_id}
    """)
    if not rows:
        return None, []
    name = rows[0].get("to_name", industry_id)
    dependents = [{"id": _rid_to_str(r.get("from_id")), "name": r.get("from_name")} for r in rows]
    return name, dependents


@tool
def forward_impact(industry: str, depth: int = 1) -> str:
    """Get what depends on an industry — what breaks if this industry is disrupted.

    Use this when the user asks things like:
    - "What depends on copper?"
    - "What would be affected if steel gets expensive?"
    - "What uses lithium?"

    If the term is ambiguous, returns dependents across ALL matching industries.

    Args:
        industry: lowercase with underscores: steel, solar_panel, copper.
        depth: 1 for direct dependents only (default), 2 to also show what depends on each dependent.
    """
    matches = _resolve_industries(industry)

    if not matches:
        return json.dumps({
            "tool": "forward_impact",
            "industry": industry,
            "depth": depth,
            "dependents": [],
            "edges": [],
            "message": f"Industry '{industry}' not found in the graph."
        })

    all_nodes = {}
    edges = []
    center_ids = set()

    for ind_id, ind_name in matches:
        center_ids.add(ind_id)
        all_nodes[ind_id] = ind_name
        _, dependents = _get_dependents(ind_id)
        for dep in dependents:
            all_nodes[dep["id"]] = dep["name"]
            edges.append({"from_id": ind_id, "from_name": ind_name,
                          "to_id": dep["id"], "to_name": dep["name"]})

            if depth >= 2:
                dep_id = dep["id"]
                if not dep_id:
                    continue
                while ":" in dep_id:
                    dep_id = dep_id.split(":", 1)[1]
                _, sub_deps = _get_dependents(dep_id)
                for sub in sub_deps:
                    edges.append({"from_id": dep["id"], "from_name": dep["name"],
                                  "to_id": sub["id"], "to_name": sub["name"]})
                    all_nodes[sub["id"]] = sub["name"]

    non_center = [{"id": k, "name": v} for k, v in all_nodes.items() if k not in center_ids]

    if not non_center:
        names = ", ".join(n for _, n in matches)
        return json.dumps({
            "tool": "forward_impact",
            "industry": industry,
            "depth": depth,
            "dependents": [],
            "edges": [],
            "message": f"No industries depend on '{names}'."
        })

    if len(matches) == 1:
        industry_name = matches[0][1]
        resolved = matches[0][0]
    else:
        industry_name = f"{industry} ({len(matches)} industries)"
        resolved = industry

    return json.dumps({
        "tool": "forward_impact",
        "industry": resolved,
        "industry_name": industry_name,
        "depth": depth,
        "center_ids": [{"id": i, "name": n} for i, n in matches],
        "dependents": non_center,
        "edges": edges,
    })


@tool
def company_exposure(industry: str) -> str:
    """Get which companies operate in a given industry.

    Use this when the user asks things like:
    - "Which companies are in copper?"
    - "Who operates in semiconductors?"
    - "What companies are exposed to steel?"

    If the term is ambiguous (e.g. "battery"), returns companies across ALL matching industries.

    Args:
        industry: lowercase with underscores: steel, solar_panel, copper, semiconductor_industry.
    """
    matches = _resolve_industries(industry)

    if not matches:
        return json.dumps({
            "tool": "company_exposure",
            "industry": industry,
            "companies": [],
            "message": f"Industry '{industry}' not found in the graph."
        })

    seen = set()
    companies = []
    matched_industries = []

    for ind_id, ind_name in matches:
        matched_industries.append({"id": ind_id, "name": ind_name})
        rows = db.query(f"""
            SELECT
                in.id AS company_id,
                in.name AS company_name,
                in.ticker AS ticker,
                in.market_cap AS market_cap,
                in.sector AS sector
            FROM operates_in
            WHERE out = industry:{ind_id}
        """)
        for row in (rows or []):
            cid = _rid_to_str(row.get("company_id"))
            if cid in seen:
                continue
            seen.add(cid)
            companies.append({
                "id": cid,
                "name": row.get("company_name"),
                "ticker": row.get("ticker"),
                "market_cap": row.get("market_cap"),
                "sector": row.get("sector"),
            })

    if not companies:
        names = ", ".join(m["name"] for m in matched_industries)
        return json.dumps({
            "tool": "company_exposure",
            "industry": industry,
            "industries_matched": matched_industries,
            "companies": [],
            "message": f"No companies found in matched industries: {names}."
        })

    companies.sort(key=lambda c: c.get("market_cap") or 0, reverse=True)

    # Use single name if exact match, otherwise label as aggregate
    if len(matched_industries) == 1:
        industry_name = matched_industries[0]["name"]
    else:
        industry_name = f"{industry} ({len(matched_industries)} industries)"

    return json.dumps({
        "tool": "company_exposure",
        "industry": industry,
        "industry_name": industry_name,
        "industries_matched": matched_industries,
        "companies": companies,
    })


def _resolve_company(raw: str) -> tuple[str | None, str | None]:
    """Resolve a user-provided company name to its SurrealDB record ID.
    Returns (id, name) or (None, None)."""
    clean = raw.lower().replace(" ", "_").replace("-", "_")
    # Try exact ID
    hit = db.query(f"SELECT id, name FROM company:{clean}")
    if hit:
        return clean, hit[0].get("name", clean)
    # Try by ticker
    rows = db.query(
        "SELECT id, name FROM company WHERE ticker != NONE AND string::uppercase(ticker) = string::uppercase($t) LIMIT 1",
        {"t": raw}
    )
    if rows:
        rid = rows[0]["id"]
        rid_str = str(rid.id) if hasattr(rid, 'id') else str(rid).split(":", 1)[-1]
        return rid_str, rows[0].get("name", rid_str)
    # Search by name
    term = raw.lower().replace("_", " ")
    rows = db.query(
        "SELECT id, name FROM company WHERE string::lowercase(name) CONTAINS string::lowercase($term) LIMIT 10",
        {"term": term}
    )
    if not rows:
        return None, None
    # Prefer exact name match, then shortest
    for row in rows:
        if row.get("name", "").lower() == term:
            rid = row["id"]
            rid_str = str(rid.id) if hasattr(rid, 'id') else str(rid).split(":", 1)[-1]
            return rid_str, row.get("name", rid_str)
    best = min(rows, key=lambda r: len(r.get("name", "") or ""))
    rid = best["id"]
    rid_str = str(rid.id) if hasattr(rid, 'id') else str(rid).split(":", 1)[-1]
    return rid_str, best.get("name", rid_str)


@tool
def company_industries(company: str) -> str:
    """Get what industries a company operates in.

    Use this when the user asks things like:
    - "What does Tesla do?"
    - "What industries is Apple in?"
    - "What sectors does BHP cover?"

    Args:
        company: company name, ticker, or ID: tesla, AAPL, rio_tinto.
    """
    comp_id, comp_name = _resolve_company(company)

    if not comp_id:
        return json.dumps({
            "tool": "company_industries",
            "company": company,
            "industries": [],
            "message": f"Company '{company}' not found in the graph."
        })

    # Get company details
    detail_rows = db.query(f"SELECT name, ticker, market_cap, sector FROM company:{comp_id}")
    detail = detail_rows[0] if detail_rows else {}

    rows = db.query(f"""
        SELECT
            out.id AS industry_id,
            out.name AS industry_name
        FROM operates_in
        WHERE in = company:{comp_id}
    """)

    industries = []
    seen = set()
    for row in (rows or []):
        iid = _rid_to_str(row.get("industry_id"))
        if iid in seen:
            continue
        seen.add(iid)
        industries.append({
            "id": iid,
            "name": row.get("industry_name"),
        })

    if not industries:
        return json.dumps({
            "tool": "company_industries",
            "company": comp_id,
            "company_name": comp_name,
            "industries": [],
            "message": f"No industries found for '{comp_name}'."
        })

    return json.dumps({
        "tool": "company_industries",
        "company": comp_id,
        "company_name": comp_name,
        "ticker": detail.get("ticker"),
        "market_cap": detail.get("market_cap"),
        "industries": industries,
    })


@tool
def shock_propagate(industry: str) -> str:
    """Simulate an economic shock — if an industry is disrupted, which industries and companies get hurt?

    Traces forward through the supply chain (what depends on this industry)
    then finds all companies operating in the affected industries.

    Use this when the user asks things like:
    - "What happens if lithium is disrupted?"
    - "Simulate a copper shortage"
    - "Who gets hurt if steel prices spike?"
    - "Shock propagation from nickel"

    Args:
        industry: the disrupted industry, lowercase with underscores: lithium, steel, copper.
    """
    matches = _resolve_industries(industry)

    if not matches:
        return json.dumps({
            "tool": "shock_propagate",
            "industry": industry,
            "affected_industries": [],
            "affected_companies": [],
            "edges": [],
            "message": f"Industry '{industry}' not found in the graph."
        })

    # Step 1: get all directly affected industries (depth 2 — two hops out)
    all_nodes = {}
    edges = []
    center_ids = set()

    for ind_id, ind_name in matches:
        center_ids.add(ind_id)
        all_nodes[ind_id] = ind_name
        _, deps = _get_dependents(ind_id)
        for dep in deps:
            all_nodes[dep["id"]] = dep["name"]
            edges.append({"from_id": ind_id, "from_name": ind_name,
                          "to_id": dep["id"], "to_name": dep["name"]})
            # Depth 2
            dep_id = dep["id"]
            if dep_id:
                while ":" in dep_id:
                    dep_id = dep_id.split(":", 1)[1]
                _, sub_deps = _get_dependents(dep_id)
                for sub in sub_deps:
                    all_nodes[sub["id"]] = sub["name"]
                    edges.append({"from_id": dep["id"], "from_name": dep["name"],
                                  "to_id": sub["id"], "to_name": sub["name"]})

    affected_industries = [{"id": k, "name": v} for k, v in all_nodes.items() if k not in center_ids]

    # Step 2: find companies in ALL affected industries (including the shocked one)
    seen_companies = set()
    affected_companies = []
    for ind_id in all_nodes:
        clean_id = ind_id
        while ":" in clean_id:
            clean_id = clean_id.split(":", 1)[1]
        rows = db.query(f"""
            SELECT
                in.id AS company_id,
                in.name AS company_name,
                in.ticker AS ticker,
                in.market_cap AS market_cap
            FROM operates_in
            WHERE out = industry:{clean_id}
        """)
        for row in (rows or []):
            cid = _rid_to_str(row.get("company_id"))
            if cid in seen_companies:
                continue
            seen_companies.add(cid)
            affected_companies.append({
                "id": cid,
                "name": row.get("company_name"),
                "ticker": row.get("ticker"),
                "market_cap": row.get("market_cap"),
            })

    affected_companies.sort(key=lambda c: c.get("market_cap") or 0, reverse=True)

    if len(matches) == 1:
        industry_name = matches[0][1]
    else:
        industry_name = f"{industry} ({len(matches)} industries)"

    return json.dumps({
        "tool": "shock_propagate",
        "industry": industry,
        "industry_name": industry_name,
        "center_ids": [{"id": i, "name": n} for i, n in matches],
        "affected_industries": affected_industries,
        "affected_companies": affected_companies,
        "edges": edges,
    })


ALL_TOOLS = [supply_chain_inputs, forward_impact, company_exposure, company_industries, shock_propagate]
