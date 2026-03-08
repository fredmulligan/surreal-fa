"""
End-to-end test chain for Surreal FA.
Tests each link in the pipeline:
1. Connectors (yfinance, wikidata, polymarket)
2. SurrealDB cloud connection
3. Schema import
4. Write node → read back
5. Write relationship → traverse
6. Graph queries
"""

import json
import sys
from dotenv import load_dotenv

load_dotenv()

PASS = 0
FAIL = 0


def test(name, fn):
    global PASS, FAIL
    try:
        result = fn()
        if result:
            print(f"  [PASS] {name}")
            PASS += 1
        else:
            print(f"  [FAIL] {name} — returned falsy")
            FAIL += 1
    except Exception as e:
        print(f"  [FAIL] {name} — {e}")
        FAIL += 1


def test_connectors():
    print("\n=== 1. CONNECTORS ===")

    def yfinance_test():
        from src.connectors.yfinance_connector import get_company_info
        info = get_company_info("AAPL")
        return info and info.get("name")

    def wikidata_test():
        from src.connectors.wikidata_connector import search_entity
        results = search_entity("Tesla")
        return results and len(results) > 0

    def polymarket_test():
        from src.connectors.polymarket_connector import search_events
        events = search_events("election")
        return isinstance(events, list)

    test("yfinance — get AAPL info", yfinance_test)
    test("wikidata — search Tesla", wikidata_test)
    test("polymarket — search events", polymarket_test)


def test_db_connection():
    print("\n=== 2. SURREALDB CONNECTION ===")

    def connect_test():
        from src.graph.db import GraphDB
        db = GraphDB()
        db.connect()
        result = db.query("INFO FOR DB")
        db.close()
        return result is not None

    test("connect to cloud SurrealDB", connect_test)


def test_schema_import():
    print("\n=== 3. SCHEMA IMPORT ===")

    def import_schema():
        from src.graph.db import GraphDB
        db = GraphDB()
        db.connect()

        # Read schema file and execute each statement
        with open("src/schema/schema.surql", "r") as f:
            schema = f.read()

        # Split into statements, skip comments and empty lines
        statements = []
        current = []
        for line in schema.split("\n"):
            stripped = line.strip()
            if stripped.startswith("--") or not stripped:
                if current:
                    stmt = " ".join(current).strip()
                    if stmt:
                        statements.append(stmt)
                    current = []
                continue
            current.append(stripped)
        if current:
            stmt = " ".join(current).strip()
            if stmt:
                statements.append(stmt)

        success = 0
        errors = 0
        for stmt in statements:
            if not stmt.endswith(";"):
                stmt += ";"
            try:
                db.query(stmt)
                success += 1
            except Exception as e:
                print(f"    Schema error: {stmt[:60]}... → {e}")
                errors += 1

        print(f"    Executed {success} statements, {errors} errors")
        db.close()
        return errors == 0

    test("import schema.surql", import_schema)


def test_write_read():
    print("\n=== 4. WRITE & READ NODES ===")

    def write_company():
        from src.graph.db import GraphDB
        db = GraphDB()
        db.connect()
        db.upsert_node("company", "test_co", {
            "name": "Test Company",
            "ticker": "TEST",
            "description": "A test company for chain verification",
            "market_cap": 1000000.0,
            "source": "test_chain",
        })
        node = db.get_node("company", "test_co")
        db.close()
        return node and node.get("name") == "Test Company"

    def write_industry():
        from src.graph.db import GraphDB
        db = GraphDB()
        db.connect()
        db.upsert_node("industry", "test_industry", {
            "name": "Test Industry",
            "source": "test_chain",
        })
        node = db.get_node("industry", "test_industry")
        db.close()
        return node and node.get("name") == "Test Industry"

    def write_commodity():
        from src.graph.db import GraphDB
        db = GraphDB()
        db.connect()
        db.upsert_node("commodity", "test_metal", {
            "name": "Test Metal",
            "category": "metal",
            "source": "test_chain",
        })
        node = db.get_node("commodity", "test_metal")
        db.close()
        return node and node.get("name") == "Test Metal"

    test("write & read company node", write_company)
    test("write & read industry node", write_industry)
    test("write & read commodity node", write_commodity)


def test_relationships():
    print("\n=== 5. RELATIONSHIPS & TRAVERSAL ===")

    def create_operates_in():
        from src.graph.db import GraphDB
        db = GraphDB()
        db.connect()
        db.create_relationship("company", "test_co", "operates_in", "industry", "test_industry")
        rels = db.get_relationships("company", "test_co", "operates_in", "out")
        db.close()
        return rels is not None

    def create_uses_input():
        from src.graph.db import GraphDB
        db = GraphDB()
        db.connect()
        db.create_relationship("company", "test_co", "uses_input", "commodity", "test_metal",
                               {"cost_sensitivity": 0.7, "criticality": "important"})
        db.close()
        return True

    def traverse_test():
        from src.graph.db import GraphDB
        db = GraphDB()
        db.connect()
        result = db.traverse("company", "test_co")
        db.close()
        return result and len(result) > 0

    test("create operates_in relationship", create_operates_in)
    test("create uses_input with properties", create_uses_input)
    test("traverse from test_co", traverse_test)


def test_graph_queries():
    print("\n=== 6. GRAPH QUERIES ===")

    def stats_test():
        from src.graph.queries import GraphQueries
        q = GraphQueries()
        stats = q.graph_stats()
        return stats and stats.get("company", 0) > 0

    def companies_in_industry_test():
        from src.graph.queries import GraphQueries
        q = GraphQueries()
        result = q.companies_in_industry("Test Industry")
        return result is not None

    test("graph_stats returns data", stats_test)
    test("companies_in_industry query", companies_in_industry_test)


def test_builder():
    print("\n=== 7. GRAPH BUILDER ===")

    def builder_test():
        from src.graph.builder import GraphBuilder
        b = GraphBuilder()
        company_id = b.add_company({
            "name": "Builder Test Corp",
            "ticker": "BTC",
            "market_cap": 5000000,
            "source": "test_chain",
        })
        industry_id = b.add_industry("Builder Test Industry")
        b.link_company_to_industry(company_id, industry_id)
        return company_id == "builder_test_corp"

    test("GraphBuilder add + link", builder_test)


def cleanup():
    print("\n=== CLEANUP ===")
    try:
        from src.graph.db import GraphDB
        db = GraphDB()
        db.connect()
        db.query("DELETE FROM company WHERE source = 'test_chain'")
        db.query("DELETE FROM industry WHERE source = 'test_chain'")
        db.query("DELETE FROM commodity WHERE source = 'test_chain'")
        print("  Cleaned up test data")
        db.close()
    except Exception as e:
        print(f"  Cleanup warning: {e}")


if __name__ == "__main__":
    print("=" * 50)
    print("  Surreal FA — End-to-End Chain Test")
    print("=" * 50)

    skip_connectors = "--skip-connectors" in sys.argv
    skip_schema = "--skip-schema" in sys.argv

    if not skip_connectors:
        test_connectors()

    test_db_connection()

    if not skip_schema:
        test_schema_import()

    test_write_read()
    test_relationships()
    test_graph_queries()
    test_builder()
    cleanup()

    print(f"\n{'=' * 50}")
    print(f"  Results: {PASS} passed, {FAIL} failed")
    print(f"{'=' * 50}\n")

    sys.exit(1 if FAIL > 0 else 0)
