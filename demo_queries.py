"""
Surreal FA — Demo Queries
==========================
Ten queries that demonstrate what the knowledge graph can do.
Each traces a different kind of economic relationship through 428 industry
nodes, 785 uses_input edges, 1165 companies, and 3231 operates_in edges.

Run: .venv/bin/python demo_queries.py
"""

from src.graph.db import GraphDB


def run_demos():
    db = GraphDB()
    db.connect()

    # ──────────────────────────────────────────────────────────
    # QUERY 1: SHOCK PROPAGATION
    # "TSMC goes offline — what breaks?"
    # ──────────────────────────────────────────────────────────
    print("=" * 70)
    print("Q1: SHOCK PROPAGATION — TSMC goes offline, what breaks?")
    print("=" * 70)

    # What does TSMC do?
    r = db.query("SELECT ->operates_in->industry.name AS ind FROM company:tsmc")
    print(f"TSMC operates in: {r[0]['ind']}")

    # What depends on semiconductor fab?
    r = db.query("""
        SELECT <-industry_uses_input<-industry.name AS users
        FROM industry:semiconductor_fabrication
    """)
    direct = r[0]['users'] if r else []
    print(f"Industries that directly need semiconductors ({len(direct)}):")
    for d in sorted(direct):
        print(f"  → {d}")

    # Companies in semiconductor fab
    r = db.query("""
        SELECT <-operates_in<-company.name AS c
        FROM industry:semiconductor_fabrication
    """)
    comps = sorted(set(x for x in r[0]['c'] if x)) if r else []
    print(f"Companies affected ({len(comps)}): {', '.join(comps)}")

    # ──────────────────────────────────────────────────────────
    # QUERY 2: SURPRISING CONNECTIONS
    # "What do a wine bottle and a smartphone have in common?"
    # ──────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("Q2: SURPRISING CONNECTIONS — Wine bottle ↔ Smartphone")
    print("=" * 70)

    r1 = db.query("""
        SELECT ->industry_uses_input->industry.name AS l1,
               ->industry_uses_input->industry->industry_uses_input->industry.name AS l2
        FROM industry:wine_bottle
    """)
    wine = set(r1[0].get('l1', [])) | set(r1[0].get('l2', []))

    r2 = db.query("""
        SELECT ->industry_uses_input->industry.name AS l1,
               ->industry_uses_input->industry->industry_uses_input->industry.name AS l2
        FROM industry:smartphone
    """)
    phone = set(r2[0].get('l1', [])) | set(r2[0].get('l2', []))

    shared = sorted(wine & phone)
    print(f"Wine bottle supply chain: {len(wine)} industries")
    print(f"Smartphone supply chain: {len(phone)} industries")
    print(f"They SHARE {len(shared)} industries: {', '.join(shared)}")
    print("→ A disruption to glass or aluminium hits both your phone and your wine.")

    # ──────────────────────────────────────────────────────────
    # QUERY 3: HUB ANALYSIS
    # "What are the economy's pressure points?"
    # ──────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("Q3: HUB ANALYSIS — Economy's pressure points")
    print("=" * 70)

    r = db.query("""
        SELECT name,
               count(<-industry_uses_input) AS dependents,
               count(->industry_uses_input) AS inputs,
               count(<-operates_in) AS companies
        FROM industry
        ORDER BY dependents DESC
        LIMIT 15
    """)
    print(f"{'Industry':<45} {'Used by':>8} {'Uses':>6} {'Cos':>5}")
    print("-" * 66)
    for row in r:
        print(f"{row['name']:<45} {row['dependents']:>8} {row['inputs']:>6} {row['companies']:>5}")

    # ──────────────────────────────────────────────────────────
    # QUERY 4: REVERSE SHOCK
    # "Copper prices double — what gets more expensive?"
    # ──────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("Q4: REVERSE SHOCK — Copper prices double")
    print("=" * 70)

    r = db.query("""
        SELECT
            <-industry_uses_input<-industry.name AS hop1,
            <-industry_uses_input<-industry<-industry_uses_input<-industry.name AS hop2,
            <-industry_uses_input<-industry<-industry_uses_input<-industry<-industry_uses_input<-industry.name AS hop3
        FROM industry:copper
    """)
    if r:
        h1 = set(r[0].get('hop1', []))
        h2 = set(r[0].get('hop2', []))
        h3 = set(r[0].get('hop3', []))
        total = h1 | h2 | h3
        print(f"Hop 1: {len(h1)} industries — {sorted(h1)}")
        print(f"Hop 2: {len(h2)} more industries")
        print(f"Hop 3: {len(h3)} more industries")
        print(f"TOTAL: {len(total)} industries affected by copper price shock")
        print("→ Copper → Electric Motor → Washing Machine, Bicycle, Wind Turbine")
        print("→ Copper → Semiconductor Fab → SoC → Smartphone")

    # ──────────────────────────────────────────────────────────
    # QUERY 5: SUPPLY CHAIN DEPTH
    # "How many steps from a washing machine to a neodymium mine?"
    # ──────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("Q5: SUPPLY CHAIN DEPTH — Washing machine → raw materials")
    print("=" * 70)

    chain = [
        ("Washing machine", "washing_machine"),
        ("  → Electric Motor", "electric_motor"),
        ("    → Neodymium Magnet", "neodymium_magnet"),
        ("      → Neodymium (rare earth)", "neodymium"),
    ]
    for label, ind_id in chain:
        r = db.query(f"SELECT ->industry_uses_input->industry.name AS i FROM industry:{ind_id}")
        inputs = r[0].get('i', []) if r else []
        suffix = f"  [{len(inputs)} inputs: {', '.join(sorted(inputs)[:5])}{'...' if len(inputs) > 5 else ''}]"
        print(f"{label}{suffix}")
    print("→ 4 hops from your laundry to a rare earth mine in Inner Mongolia")

    # ──────────────────────────────────────────────────────────
    # QUERY 6: CONGLOMERATE MAP
    # "Which companies span the most industries?"
    # ──────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("Q6: CONGLOMERATE MAP — Companies spanning industries")
    print("=" * 70)

    r = db.query("""
        SELECT name,
               array::distinct(->operates_in->industry.name) AS industries,
               count(array::distinct(->operates_in->industry)) AS span
        FROM company
        ORDER BY span DESC
        LIMIT 12
    """)
    for row in r:
        span = row.get('span', 0)
        if span > 1:
            inds = row.get('industries', [])
            print(f"  {row['name']:<35} {span} industries: {', '.join(inds)}")

    # ──────────────────────────────────────────────────────────
    # QUERY 7: CROSS-SECTOR CONTAGION
    # "A bearing factory fire — who cares?"
    # ──────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("Q7: CROSS-SECTOR CONTAGION — Bearing factory fire")
    print("=" * 70)

    r = db.query("""
        SELECT
            <-industry_uses_input<-industry.name AS direct,
            <-industry_uses_input<-industry<-industry_uses_input<-industry.name AS cascade
        FROM industry:bearing
    """)
    if r:
        direct = sorted(set(r[0].get('direct', [])))
        cascade = sorted(set(r[0].get('cascade', [])))
        print(f"Bearings go into {len(direct)} industries: {', '.join(direct)}")
        print(f"Those cascade into {len(cascade)} more: {', '.join(cascade)}")

    r2 = db.query("""
        SELECT <-industry_uses_input<-industry<-operates_in<-company.name AS c
        FROM industry:bearing
    """)
    if r2 and r2[0].get('c'):
        comps = sorted(set(x for x in r2[0]['c'] if x))
        print(f"{len(comps)} companies feel the pain: {', '.join(comps[:15])}...")
    print("→ One bearing factory connects bicycles, washing machines, and wind turbines")

    # ──────────────────────────────────────────────────────────
    # QUERY 8: CRUDE TO CURE
    # "Oil prices spike — does medicine get more expensive?"
    # ──────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("Q8: CRUDE TO CURE — Oil prices spike → medicine costs")
    print("=" * 70)

    chain = [
        ("Petroleum", "petroleum"),
        ("  → Oil refinery", "oil_refinery"),
        ("    → Benzene", "benzene"),
        ("      → API synthesis", "api_synthesis"),
    ]
    for label, ind_id in chain:
        r = db.query(f"SELECT ->industry_uses_input->industry.name AS i FROM industry:{ind_id}")
        inputs = r[0].get('i', []) if r else []
        r2 = db.query(f"SELECT <-industry_uses_input<-industry.name AS u FROM industry:{ind_id}")
        users = r2[0].get('u', []) if r2 else []
        print(f"{label}  [needs {len(inputs)} inputs, feeds {len(users)} industries]")

    # What drug classes need API synthesis?
    r = db.query("""
        SELECT <-industry_uses_input<-industry.name AS drugs
        FROM industry:api_synthesis
    """)
    if r:
        drugs = sorted(r[0].get('drugs', []))
        print(f"Drug classes needing API synthesis: {', '.join(drugs)}")

    # Companies in the pharma chain
    r = db.query("""
        SELECT <-operates_in<-company.name AS c
        FROM industry:api_synthesis
    """)
    if r and r[0].get('c'):
        print(f"API manufacturers affected: {', '.join(sorted(set(x for x in r[0]['c'] if x)))}")
    print("→ Crude oil → benzene → drug synthesis → your cholesterol pill")

    # ──────────────────────────────────────────────────────────
    # QUERY 9: GLOBAL TRADE SHOCK
    # "Steel shortage → shipping grinds to a halt"
    # ──────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("Q9: GLOBAL TRADE SHOCK — Steel shortage → shipping stops")
    print("=" * 70)

    r = db.query("""
        SELECT <-industry_uses_input<-industry.name AS users
        FROM industry:steel
    """)
    if r:
        users = sorted(r[0].get('users', []))
        shipping = [u for u in users if any(k in u.lower() for k in ['ship', 'container', 'crane', 'marine'])]
        print(f"Steel feeds {len(users)} industries total")
        print(f"Shipping/logistics industries needing steel: {', '.join(shipping)}")

    # Trace: steel → shipping container → container shipping → what?
    r = db.query("""
        SELECT <-industry_uses_input<-industry.name AS l1,
               <-industry_uses_input<-industry<-industry_uses_input<-industry.name AS l2
        FROM industry:shipping_container
    """)
    if r:
        l1 = sorted(set(r[0].get('l1', [])))
        l2 = sorted(set(r[0].get('l2', [])))
        print(f"Shipping container feeds: {', '.join(l1)}")
        print(f"Which feed: {', '.join(l2)}")

    # Companies affected
    r = db.query("""
        SELECT <-operates_in<-company.name AS c
        FROM industry:container_shipping
    """)
    if r and r[0].get('c'):
        print(f"Shipping lines affected: {', '.join(sorted(set(x for x in r[0]['c'] if x)))}")
    print("→ A steel shortage doesn't just hit cars — it hits every port on Earth")

    # ──────────────────────────────────────────────────────────
    # QUERY 10: GLASS BOTTLENECK
    # "Glass shortage — wine, phones, AND vaccines?"
    # ──────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("Q10: GLASS BOTTLENECK — One material, three crises")
    print("=" * 70)

    r = db.query("""
        SELECT <-industry_uses_input<-industry.name AS users
        FROM industry:glass
    """)
    if r:
        users = sorted(r[0].get('users', []))
        print(f"Glass is used by {len(users)} industries:")
        for u in users:
            print(f"  → {u}")

    # Find the surprising overlap: consumer + medical + energy
    r = db.query("""
        SELECT <-industry_uses_input<-industry<-operates_in<-company.name AS c
        FROM industry:glass
    """)
    if r and r[0].get('c'):
        comps = sorted(set(x for x in r[0]['c'] if x))
        print(f"{len(comps)} companies depend on glass: {', '.join(comps[:20])}...")
    print("→ One glass factory connects your wine, your phone, your vaccine, and your solar panel")

    db.close()
    print("\n\n✓ All 10 demo queries complete")


if __name__ == "__main__":
    run_demos()
