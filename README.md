# Surreal FA — Surreal Financial Advice

**Ask what happens if X. Get the consequences nobody's thinking about.**

Surreal FA traces economic shockwaves through a knowledge graph of the real economy — companies, industries, supply chains, commodities, policies — to surface the second- and third-order effects that analysts miss because they think in sectors, not in graphs.

"What happens if China invades Taiwan?" → TSMC goes offline → 90% of advanced chips disappear → Apple, Nvidia, AMD can't ship → data center buildout stalls → AI boom slows → but legacy chip makers surge → meanwhile copper demand shifts, semiconductor-grade neon from Ukraine matters again, and a toy company in Shenzhen that nobody was watching quietly goes under.

The further from the epicenter, the more surreal — and the more valuable.

## How It Works

Surreal FA has two sides:

### 1. The Graph Engine (the kitchen)

Agents iteratively build and enrich a knowledge graph of the economy. They pull from structured data sources (yfinance, Wikidata), read unstructured sources (Wikipedia, news), extract entities and relationships, and store everything in SurrealDB. The graph gets denser over time — more companies, more supply chain links, more commodity dependencies, more policy connections.

This runs in the background. You can watch it work, steer it toward industries you care about, and see the graph grow. It's fascinating to watch, but it's infrastructure.

### 2. Shock Propagation (the product)

Once the graph is rich, you ask questions:

- *"What happens if copper prices double?"*
- *"What if the EU passes carbon tariffs?"*
- *"AI boom accelerates — who loses?"*

The system traces the shock through the graph edge by edge. First-order effects are obvious. Second-order effects are expected. Third-order effects are where the surreal financial advice lives — the connections that a human staring at Bloomberg would never make because the path runs through four different industries and two commodity markets.

### 3. Polymarket Integration (the probability layer)

Polymarket gives us crowd-priced probabilities on real events. Instead of purely hypothetical "what ifs", Surreal FA can show: "There's a 72% chance the EU passes carbon tariffs by 2027. If that hits, here's the cascade, weighted by likelihood."

When no Polymarket market exists for an event, the agent breaks it into sub-questions, finds adjacent markets, and synthesizes a probability estimate.

## The Graph

### What's in it

| Node Type | Examples | Why it matters |
|-----------|----------|---------------|
| `industry` | Cloud Computing, EVs, Mining | The sectors of the economy |
| `company` | Tesla, TSMC, Shopify | The players |
| `technology` | Lidar, Solid State Batteries | What they're betting on |
| `product` | Model 3, Azure, Stripe Payments | What they sell |
| `commodity` | Copper, Lithium, Electricity | The raw inputs everything depends on |
| `policy` | CHIPS Act, EU Carbon Tariffs | Government distortions to the graph |
| `event` | AI Boom, Trade War | Shocks with Polymarket probabilities |

### How things connect

| Relationship | Example | What it enables |
|-------------|---------|----------------|
| `OPERATES_IN` | Tesla → EV Industry | Map the players |
| `COMPETES_WITH` | Uber ↔ Lyft | Who eats whose lunch |
| `SUPPLIES_TO` | TSMC → Apple | Supply chain cascades |
| `COMPLEMENT_OF` | Shopify ↔ Stripe | Things that rise and fall together |
| `SUBSTITUTE_FOR` | Zoom ↔ Teams | When one dies, the other thrives |
| `SUBSIDIARY_OF` | Waymo → Alphabet | Ownership chains |
| `USES_TECHNOLOGY` | Tesla → Pure Vision | Technology bets |
| `INVESTED_IN` | Microsoft → OpenAI | Money flows |
| `USES_INPUT` | Tesla → Lithium | Commodity exposure (with cost sensitivity) |
| `SUBSTITUTE_INPUT` | Copper ↔ Aluminum | Can they switch? At what cost? |
| `DEMAND_DRIVER` | AI Boom → GPU Demand | What events push demand where |
| `AFFECTED_BY_POLICY` | EV Makers → IRA Subsidies | Policy tailwinds and headwinds |

Every edge carries properties — cost sensitivity, revenue dependency, confidence, criticality — because "Tesla uses lithium" is less useful than "lithium is 15% of Tesla's battery cost and there's no substitute at scale."

## Data Sources

| Source | What We Get | Auth |
|--------|------------|------|
| yfinance | Sector, industry, market cap, competitors, descriptions | None |
| Wikidata SPARQL | Company→parent, products, industry, founders | None |
| Wikipedia | Industry overviews, player/tech extraction | None |
| Polymarket | Event probabilities, prediction markets | None |
| SEC EDGAR | Company filings, relationships (stretch) | None |
| News API | Current events, shock triggers (stretch) | API key |

## Tech Stack

- **LangChain / LangGraph** — agent orchestration, tool use, state machine for the graph-building agent
- **SurrealDB** — graph + document + vector database in one. The graph lives here.
- **Python 3.13**

## Build Plan (Weekend)

### Phase 1 — Graph engine, one industry (Saturday AM)
Get the agent loop working: pick "Electric Vehicles" → pull companies from yfinance/Wikidata → extract relationships → store in SurrealDB. End-to-end pipeline.

### Phase 2 — Enrich and expand (Saturday PM)
Deepen: technologies, supply chains, commodity inputs, complements, substitutes. Widen: agent discovers adjacent industries (Battery Manufacturing, Charging Infrastructure) and builds those out. The graph gets dense enough to be useful.

### Phase 3 — Shock propagation (Sunday AM)
The product. Inject an event → traverse the graph → trace consequences → surface the third-hop surprises. This is what we demo.

### Phase 4 — Polymarket + polish (Sunday AM/PM)
Probability layer, natural language query interface, graph visualization, demo prep.

## Team Split (5 people)

1. **SurrealDB + data model** — schema, queries, graph visualization
2. **Data source connectors** — yfinance, Wikidata, Wikipedia, Polymarket
3. **LangGraph agent loop** — the graph-building state machine
4. **LLM extraction** — unstructured text → entities and relationships
5. **Frontend / demo** — shock propagation UI, graph rendering, the 2-minute pitch

## Setup

```bash
# Virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Start SurrealDB
surreal start --log trace --user root --pass root memory
# Or persistent: surreal start --log trace --user root --pass root file:surreal_fa.db

# Load schema
surreal import --conn http://localhost:8000 --user root --pass root --ns surreal_fa --db surreal_fa src/schema/schema.surql

# Build the graph (graph engine)
python -m src.agent.build "Electric Vehicles"

# Ask a question (the product)
python -m src.agent.shock "What happens if copper prices double?"
```

## Project Structure

```
surreal-fa/
├── src/
│   ├── connectors/       # Data source integrations
│   │   ├── yfinance_connector.py
│   │   ├── wikidata_connector.py
│   │   ├── polymarket_connector.py
│   │   └── wikipedia_connector.py
│   ├── graph/             # Graph operations
│   │   ├── builder.py     # Entity/relationship extraction → SurrealDB
│   │   ├── shock.py       # Shock propagation engine
│   │   └── queries.py     # Graph traversal queries
│   ├── schema/
│   │   └── schema.surql   # SurrealDB schema
│   └── agent/             # LangGraph agents
│       ├── build.py       # Graph-building agent (the kitchen)
│       ├── shock.py       # Shock propagation agent (the product)
│       ├── state.py       # Agent state definitions
│       └── tools.py       # LangChain tools
├── docs/
│   └── langchain_cheatsheet.md
├── tests/
├── requirements.txt
├── .env.example
└── README.md
```

---

*Built at the LangChain x SurrealDB London Hackathon, March 2026*
