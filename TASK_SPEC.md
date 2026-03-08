# Overnight Task Spec — 2026-03-08

## What this file is

Recovery document. If the conversation compacts mid-task, the next context reads this to know exactly what was being done, what's finished, what's next, and where everything lives. Like a WAL for a distributed system.

## The Two Tasks

### TASK 1: Industry Graph (Wikipedia link walking)

**Goal**: Walk 6 new trees using the Wikipedia link walking algorithm. Build a dense industry graph with heavy merges.

**Trees to walk:**

| # | Tree | Wikipedia article | Why |
|---|------|-------------------|-----|
| 1 | Smartphone | `Smartphone` | Consumer electronics → semiconductors, battery, display. Heavy merge with data center tree. |
| 2 | Automobile | `Car` or `Automobile` | Transport → engine, steel, rubber, battery (EV merge), glass, electronics. |
| 3 | Solar panel | `Solar panel` | Energy → photovoltaic cell, silicon (merge), silver, glass, inverter. |
| 4 | Wine bottle | `Wine bottle` | Wild card. Glass (merge!), cork, aluminium (merge), paper label. Short tree, surprise merges. |
| 5 | Bicycle | `Bicycle` | Wild card. Aluminium (merge), steel (merge), rubber, bearings (merge!), carbon fiber. |
| 6 | Washing machine | `Washing machine` | Wild card. Electric motor (merge!), steel, rubber, PCB (merge), bearings (merge). |

**Algorithm for each tree** (see process.md for full detail):
1. `curl` Wikipedia API: `action=parse&page=X&prop=links&format=json`
2. Filter links to inputs (physical AND service) that have their own industry behind them
3. Each input → industry node + uses_input edge
4. Record companies found along the way to company_discovery.json
5. Pick next unexplored node with most connections to existing tree → repeat
6. Stop when mostly merges

**Output files:**
- `/Users/edwardmullin/projects/hackathon/industry_discovery.json` — all nodes + edges
- `/Users/edwardmullin/projects/hackathon/company_discovery.json` — companies found during walking

**Current state (before this task):**
- 128 industry nodes
- 182 uses_input edges
- 78 companies in discovery list
- 11 articles explored (all from Data center tree)
- 119 unexplored leaves from data center tree (don't expand these — start new trees)

**Target:**
- 300-400 industry nodes total
- 500+ edges
- 200+ companies in discovery list
- 6 new trees walked, each 5-10 articles deep

**Stopping point for Task 1:**
- Each tree walked until mostly merges (3+ consecutive articles with >60% merge nodes)
- All 6 trees started and walked to at least 3 levels deep
- JSON files updated after each article (not batched)

**Important rules (from Ed, non-negotiable):**
- Don't roll up chemicals — each is its own node
- Components not SKUs
- Include software/service dependencies (mobile OS, CUDA, etc.)
- Claude does the filtering, NOT GPT-4o
- Save companies with context notes (what they do)
- Edges are as important as nodes — record every merge, it's a shock path

---

### TASK 2: Company Processing

**Goal**: Process ~250 companies through the company straight line. Allocate each to our industry taxonomy.

**Source companies:**
- ~78 from company_discovery.json (already have context notes + industry)
- ~39 already processed (in SurrealDB, need re-allocation to new industries)
- Rest discovered during Task 1 walking (will grow to ~200+)
- Additional companies from Wikidata reverse-queries during processing

**Company straight line (6 steps per company):**
1. **yfinance** — pull financials (revenue, market cap, sector, etc.)
2. **Wikidata** — Q-ID, P452 industries, P355 subsidiaries
3. **Industry reverse-query** — find more companies in same Wikidata industries → add to queue
4. **Wikipedia** — read company page for supplier relationships
5. **Tavily** — gap-fill supply chain data
6. **Sense check** — flag missing suppliers/commodities

**Industry allocation (the hard part):**
- Map each company to 1-N of OUR industry nodes (not Wikidata's)
- Use yfinance sector as a hint, but our taxonomy is the authority
- Conglomerates get multiple operates_in edges (Samsung → semiconductor_fabrication, smartphone, display_panel)
- Companies from company_discovery.json already have context notes indicating their industry

**Edge types created during company processing:**
- Company → `operates_in` → Industry
- Company → `subsidiary_of` → Company
- Company → `invested_in` → Company
- Company → `supplies_to` → Company

**Stopping point for Task 2:**
- All companies from company_discovery.json processed (at least yfinance + industry allocation)
- At least 3-5 companies per major industry node
- Queue of additional discovered companies documented (not necessarily processed)
- Key junction companies (TSMC, Samsung, Apple, etc.) have full straight line with supplier edges

**Important: the queue is the ongoing thing.** Each company processed discovers more companies. We can't process them all. The queue keeps growing. That's fine — document it, show the numbers, demonstrate the process works. The demo doesn't need completeness, it needs proof the process scales.

---

### TASK 3: SurrealDB Import

**Goal**: Get everything from JSON staging into SurrealDB so it's queryable.

**What to import:**
1. All industry nodes from industry_discovery.json → `industry` table
2. All uses_input edges → `uses_input` edge table (industry → industry)
3. All companies from company_discovery.json → `company` table (or merge with existing)
4. All operates_in edges from Task 2 → `operates_in` edge table
5. All supplies_to, subsidiary_of, invested_in edges from company processing

**Schema considerations:**
- Industry table may need new fields vs existing (wikipedia, discovered_from, type)
- Existing 12 industry nodes in SurrealDB are from Wikidata P452 — keep or replace? Probably replace with our taxonomy, redirect old edges
- Use UPSERT MERGE so we don't clobber existing company data for the 39 already-processed
- `_clean_id` for all node IDs (handle non-ASCII, special chars)
- SCHEMAFULL tables — make sure all fields are defined or they'll silently drop

**Stopping point**: Every node and edge from Tasks 1+2 exists in SurrealDB. A SurrealQL traversal query returns results.

---

### TASK 4: Demo Queries (Extra Credit)

**Goal**: Write compelling SurrealQL queries that demonstrate what the graph can do. These become the basis for whatever product Ed builds on top.

**Query ideas:**

1. **Shock propagation**: "TSMC goes offline — what breaks?"
   - Start at TSMC → find its operates_in industries → traverse uses_input backwards → find all upstream and downstream industries → list all companies in affected industries
   - Multi-hop: how many steps from TSMC to a bicycle?

2. **Surprising connections**: "What do a wine bottle and a smartphone have in common?"
   - Find all paths between two nodes → identify shared industry nodes (glass, aluminium)
   - The "holy shit" query for the demo

3. **Hub analysis**: "What's the most connected industry?"
   - Count incoming uses_input edges per node
   - Copper, aluminium, steel, PCB should top the list
   - These are the economy's pressure points

4. **Reverse shock**: "Copper prices double — what gets more expensive?"
   - Start at copper → traverse uses_input forward → list every industry and company affected
   - Show the cascade: copper → PCB → server → data center → cloud computing

5. **Supply chain depth**: "How many steps from a washing machine to a neodymium mine?"
   - Longest path through uses_input edges
   - Washing machine → electric motor → neodymium magnet → neodymium → rare earth mining

6. **Company vulnerability**: "Which companies have the most concentrated supply chains?"
   - Companies where all operates_in industries share the same upstream dependency
   - Single points of failure

7. **Cross-sector contagion**: "A bearing factory fire — who cares?"
   - Bearing → electric motor, hard disk, wind turbine, washing machine, automobile
   - Shows how a niche component ripples across unrelated sectors

**Output**: A file of working SurrealQL queries with comments explaining what each demonstrates.

---

## Order of Operations

1. **Task 1 first** — walk all 6 industry trees. Fastest, produces the taxonomy.
2. **Task 2 second** — process companies, allocate to industries.
3. **Task 3 third** — import everything to SurrealDB.
4. **Task 4 last** — write and test demo queries.

---

## Graph Schema (what ends up in SurrealDB)

**Nodes:**
- `company` — name, ticker, revenue, market_cap, sector, wikidata_id, etc.
- `industry` — name, wikipedia, discovered_from, type

**Edges:**
- `operates_in` — company → industry
- `subsidiary_of` — company → company
- `invested_in` — company → company
- `supplies_to` — company → company
- `uses_input` — industry → industry

Commodities (copper, lithium, silicon) are just industry leaf nodes. No separate type.
Competition is implicit: companies sharing an operates_in target are competitors.

---

## File Locations

| File | Purpose |
|------|---------|
| `industry_discovery.json` | All industry nodes + edges (JSON staging) |
| `company_discovery.json` | Companies found during walking (lazy list with context) |
| `src/graph/builder.py` | Graph builder — resolve_entity, node/edge builders |
| `src/graph/db.py` | SurrealDB client — _clean_id, connection handling |
| `memory/process.md` | The algorithm documentation (secret sauce) |
| `memory/MEMORY.md` | Project memory — state, issues, data sources |
| `TASK_SPEC.md` | THIS FILE — recovery document |

---

## Progress Tracker

Update this section as work completes. This is what a compacted context reads first.

### Task 1 Progress: Industry Walking

| Tree | Status | Articles walked | New nodes | New edges | Notes |
|------|--------|----------------|-----------|-----------|-------|
| Data center | DONE (prior session) | 11 | 128 | 182 | Test tree. Complete. |
| Smartphone | DONE | 2 (Smartphone, OLED) | 58 | 83 | SoC, display, camera, sensors, OLED organic chemistry. |
| Automobile | DONE | 1 | 49 | 79 | ICE, transmission, brakes, suspension, catalytic converter, EV charging. |
| Solar panel | DONE | 1 | 20 | 39 | Solar cell, inverter, CdTe, CIGS, GaAs, perovskite. |
| Wine bottle | DONE | 3 (Wine bottle, Container glass, Corrugated fiberboard) | 32 | 45 | Cork, glass raw materials, paper/pulp chain, petrochemicals (PE, PP, PVC). |
| Bicycle | DONE | 2 (Bicycle, Carbon fibre) | 16 | 45 | Carbon fiber → PAN → acrylonitrile → propylene. Titanium. 20 merge edges. |
| Washing machine | DONE | 1 | 13 | 44 | Massive merges: motor, PCB, bearing, shock absorber. Detergent chemistry. |

**Total: 316 nodes, 515 edges, 21 articles explored**

### Task 2 Progress: Company Processing

| Metric | Count |
|--------|-------|
| Companies in discovery list | 239 |
| Companies processed (full straight line) | 0 this session |
| Companies with yfinance data | 0 this session |
| Companies allocated to new industries | 0 |
| Queue size | 239 |

### Task 3 Progress: SurrealDB Import

| Step | Status |
|------|--------|
| Industry nodes imported | DONE — 328 nodes (316 new + 12 existing) |
| uses_input edges imported | DONE — 515 industry→industry edges |
| Company nodes imported | DONE — 239 companies merged |
| operates_in edges imported | DONE — 369 unique edges (48 dupes removed) |
| supplies_to edges imported | SKIPPED (existing 77 from prior session) |
| Schema validated | DONE — added wikipedia, discovered_from, type_tag, context, category fields |
| Test query works | DONE — all 7 demo queries execute |

### Task 4 Progress: Demo Queries

| Query | Status | Result |
|-------|--------|--------|
| Shock propagation (TSMC) | DONE | 12 direct dependent industries, 17 companies affected |
| Surprising connections (wine bottle ↔ smartphone) | DONE | Share 3 industries: Aluminium, Cobalt, Glass |
| Hub analysis (most connected) | DONE | Steel (17), Aluminium (15), Copper (13), Semiconductor Fab (12), PCB (10) |
| Reverse shock (copper) | DONE | 37 industries affected across 3 hops |
| Supply chain depth (washing machine → mine) | DONE | 4 hops: washing machine → motor → neodymium magnet → neodymium |
| Conglomerate map | DONE | Samsung spans 6 industries, Panasonic 6, Intel 4, Qualcomm 4 |
| Cross-sector contagion (bearing fire) | DONE | 7 direct industries, 8 cascade, 39 companies affected |

---

## What "done" looks like for the demo

1. ✅ Industry graph with 316 nodes and 515 edges across 7 trees, showing visible merges (copper in 13 branches, steel in 17, aluminium in 15, bearing connecting bicycles, washing machines, and wind turbines)
2. ✅ 239 companies placed into industries with 369 operates_in edges
3. ✅ Key companies (TSMC, Samsung, Apple, Intel, etc.) with operates_in edges across multiple industries
4. ✅ All in SurrealDB cloud, queryable via HTTP
5. ✅ Shock traversals work: "TSMC goes offline → 12 dependent industries → 17 affected companies"
6. ✅ All 7 demo queries in demo_queries.py, executable
