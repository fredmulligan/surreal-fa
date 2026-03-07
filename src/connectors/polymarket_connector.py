"""
Polymarket connector — prediction market probabilities for real events.
Public API, no key needed for reading market data.
"""

import httpx

POLYMARKET_API = "https://gamma-api.polymarket.com"


def search_markets(query: str, limit: int = 10) -> list[dict]:
    """
    Search Polymarket for prediction markets matching a query.
    Returns markets with current probabilities.
    """
    try:
        resp = httpx.get(
            f"{POLYMARKET_API}/markets",
            params={"tag": query, "limit": limit, "active": True, "closed": False},
            timeout=15,
        )
        resp.raise_for_status()
        markets = resp.json()

        # Also try text search
        resp2 = httpx.get(
            f"{POLYMARKET_API}/markets",
            params={"limit": limit, "active": True, "closed": False},
            timeout=15,
        )
        resp2.raise_for_status()

        results = []
        for market in markets if isinstance(markets, list) else []:
            results.append(_parse_market(market))
        return results
    except Exception as e:
        print(f"Polymarket error: {e}")
        return []


def search_events(query: str, limit: int = 10) -> list[dict]:
    """
    Search Polymarket events (which contain multiple markets).
    """
    try:
        resp = httpx.get(
            f"{POLYMARKET_API}/events",
            params={"tag": query, "limit": limit, "active": True, "closed": False},
            timeout=15,
        )
        resp.raise_for_status()
        events = resp.json()

        results = []
        for event in events if isinstance(events, list) else []:
            markets = []
            for m in event.get("markets", []):
                markets.append(_parse_market(m))
            results.append({
                "id": event.get("id"),
                "title": event.get("title", ""),
                "description": event.get("description", ""),
                "markets": markets,
                "source": "polymarket",
            })
        return results
    except Exception as e:
        print(f"Polymarket events error: {e}")
        return []


def get_market(market_id: str) -> dict | None:
    """Get details for a specific market."""
    try:
        resp = httpx.get(f"{POLYMARKET_API}/markets/{market_id}", timeout=15)
        resp.raise_for_status()
        return _parse_market(resp.json())
    except Exception as e:
        print(f"Polymarket market error: {e}")
        return None


def _parse_market(market: dict) -> dict:
    """Parse a market response into a clean dict."""
    # outcomePrices is a JSON string of probabilities
    prices_str = market.get("outcomePrices", "[]")
    try:
        import json
        prices = json.loads(prices_str) if isinstance(prices_str, str) else prices_str
    except (json.JSONDecodeError, TypeError):
        prices = []

    outcomes_str = market.get("outcomes", "[]")
    try:
        import json
        outcomes = json.loads(outcomes_str) if isinstance(outcomes_str, str) else outcomes_str
    except (json.JSONDecodeError, TypeError):
        outcomes = []

    # Build outcome probability pairs
    outcome_probs = {}
    for i, outcome in enumerate(outcomes):
        if i < len(prices):
            try:
                outcome_probs[outcome] = float(prices[i])
            except (ValueError, TypeError):
                pass

    return {
        "id": market.get("id"),
        "question": market.get("question", ""),
        "description": market.get("description", ""),
        "outcomes": outcome_probs,
        "volume": market.get("volume"),
        "liquidity": market.get("liquidity"),
        "end_date": market.get("endDate"),
        "active": market.get("active", False),
        "closed": market.get("closed", False),
        "source": "polymarket",
    }


if __name__ == "__main__":
    import json

    # Test: search for AI-related markets
    events = search_events("AI")
    print(f"Found {len(events)} events:")
    for e in events[:3]:
        print(f"  {e['title']}")
        for m in e.get("markets", [])[:2]:
            print(f"    {m['question']}: {m['outcomes']}")
