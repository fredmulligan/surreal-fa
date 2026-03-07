"""
Wikidata SPARQL connector — structured company and industry relationships.
No API key needed. Use the public SPARQL endpoint.
"""

import requests

WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"
HEADERS = {"User-Agent": "SurrealFA/1.0 (hackathon project)"}


def _run_sparql(query: str) -> list[dict]:
    """Execute a SPARQL query against Wikidata."""
    try:
        resp = requests.get(
            WIKIDATA_SPARQL_URL,
            params={"query": query, "format": "json"},
            headers=HEADERS,
            timeout=30,
        )
        resp.raise_for_status()
        results = resp.json()
        return results.get("results", {}).get("bindings", [])
    except Exception as e:
        print(f"Wikidata SPARQL error: {e}")
        return []


def get_companies_in_industry(industry_name: str) -> list[dict]:
    """
    Find companies in an industry via Wikidata.
    Searches by industry label and returns companies with key properties.
    """
    query = f"""
    SELECT DISTINCT ?company ?companyLabel ?ticker ?countryLabel ?inception ?parentLabel WHERE {{
      ?company wdt:P31 wd:Q4830453 .  # instance of business enterprise (or subclass)
      ?company wdt:P452 ?industry .    # industry
      ?industry rdfs:label ?industryLabel .
      FILTER(LANG(?industryLabel) = "en")
      FILTER(CONTAINS(LCASE(?industryLabel), LCASE("{industry_name}")))

      OPTIONAL {{ ?company wdt:P249 ?ticker . }}
      OPTIONAL {{ ?company wdt:P17 ?country . }}
      OPTIONAL {{ ?company wdt:P571 ?inception . }}
      OPTIONAL {{ ?company wdt:P749 ?parent . }}

      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
    }}
    LIMIT 50
    """
    results = _run_sparql(query)
    companies = []
    for r in results:
        companies.append({
            "name": r.get("companyLabel", {}).get("value", ""),
            "wikidata_id": r.get("company", {}).get("value", "").split("/")[-1],
            "ticker": r.get("ticker", {}).get("value"),
            "country": r.get("countryLabel", {}).get("value"),
            "inception": r.get("inception", {}).get("value"),
            "parent": r.get("parentLabel", {}).get("value"),
            "source": "wikidata",
        })
    return companies


def get_company_relationships(wikidata_id: str) -> dict:
    """
    Get all interesting relationships for a company from Wikidata.
    Returns subsidiaries, parent companies, products, founders, etc.
    """
    query = f"""
    SELECT ?propLabel ?valueLabel ?value WHERE {{
      wd:{wikidata_id} ?prop ?value .
      ?property wikibase:directClaim ?prop .
      ?property rdfs:label ?propLabel .
      FILTER(LANG(?propLabel) = "en")
      FILTER(?prop IN (
        wdt:P749,   # parent organization
        wdt:P355,   # subsidiary
        wdt:P1056,  # product or material produced
        wdt:P452,   # industry
        wdt:P112,   # founded by
        wdt:P169,   # CEO
        wdt:P17,    # country
        wdt:P159,   # HQ location
        wdt:P1830,  # owner of
        wdt:P127,   # owned by
        wdt:P1344,  # participant in
        wdt:P2541   # operating area
      ))
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
    }}
    """
    results = _run_sparql(query)
    relationships = {}
    for r in results:
        prop = r.get("propLabel", {}).get("value", "")
        val = r.get("valueLabel", {}).get("value", "")
        val_id = r.get("value", {}).get("value", "").split("/")[-1]
        if prop not in relationships:
            relationships[prop] = []
        relationships[prop].append({"label": val, "id": val_id})
    return relationships


def get_supply_chain(wikidata_id: str) -> dict:
    """
    Find supply chain relationships: what a company uses and produces.
    """
    query = f"""
    SELECT ?relationLabel ?itemLabel ?item WHERE {{
      {{
        wd:{wikidata_id} wdt:P1056 ?item .  # product or material produced
        BIND("produces" AS ?relation)
      }} UNION {{
        wd:{wikidata_id} wdt:P2283 ?item .  # uses
        BIND("uses" AS ?relation)
      }} UNION {{
        ?item wdt:P1056 ?product .
        wd:{wikidata_id} wdt:P2283 ?product .
        BIND("supplier" AS ?relation)
      }}
      BIND(?relation AS ?relationLabel)
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
    }}
    LIMIT 50
    """
    results = _run_sparql(query)
    supply_chain = {"produces": [], "uses": [], "suppliers": []}
    for r in results:
        relation = r.get("relationLabel", {}).get("value", "")
        item = r.get("itemLabel", {}).get("value", "")
        item_id = r.get("item", {}).get("value", "").split("/")[-1]
        if relation in supply_chain:
            supply_chain[relation].append({"label": item, "id": item_id})
    return supply_chain


def search_entity(name: str, entity_type: str = "company") -> list[dict]:
    """
    Search Wikidata for an entity by name.
    """
    try:
        resp = requests.get(
            "https://www.wikidata.org/w/api.php",
            params={
                "action": "wbsearchentities",
                "search": name,
                "language": "en",
                "format": "json",
                "limit": 5,
            },
            headers=HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            {
                "id": item["id"],
                "label": item.get("label", ""),
                "description": item.get("description", ""),
            }
            for item in data.get("search", [])
        ]
    except Exception as e:
        print(f"Wikidata search error: {e}")
        return []


if __name__ == "__main__":
    import json

    # Test: find EV companies
    companies = get_companies_in_industry("automotive")
    print(f"Found {len(companies)} companies:")
    for c in companies[:5]:
        print(f"  {c['name']} ({c['wikidata_id']})")

    # Test: get Tesla relationships
    rels = get_company_relationships("Q478214")  # Tesla's Wikidata ID
    print(json.dumps(rels, indent=2))
