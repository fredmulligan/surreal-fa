-- Surreal FA — Knowledge Graph Schema
-- Run: surreal import --conn http://localhost:8000 --user root --pass root --ns surreal_fa --db surreal_fa src/schema/schema.surql

-- ============================================================
-- NODE TABLES
-- ============================================================

-- Industries / Sectors
DEFINE TABLE industry SCHEMAFULL;
DEFINE FIELD name ON TABLE industry TYPE string;
DEFINE FIELD description ON TABLE industry TYPE option<string>;
DEFINE FIELD sector ON TABLE industry TYPE option<string>;
DEFINE FIELD wikidata_id ON TABLE industry TYPE option<string>;
DEFINE FIELD yfinance_name ON TABLE industry TYPE option<string>;
DEFINE FIELD market_size_usd ON TABLE industry TYPE option<float>;
DEFINE FIELD growth_rate ON TABLE industry TYPE option<float>;
DEFINE FIELD barriers_to_entry ON TABLE industry TYPE option<array<string>>;
DEFINE FIELD key_regulations ON TABLE industry TYPE option<array<string>>;
DEFINE FIELD source ON TABLE industry TYPE option<string>;
DEFINE FIELD status ON TABLE industry TYPE option<string>; -- stub, processed
DEFINE FIELD created_at ON TABLE industry TYPE datetime VALUE time::now();
DEFINE FIELD updated_at ON TABLE industry TYPE option<datetime> VALUE time::now();
DEFINE INDEX idx_industry_name ON TABLE industry COLUMNS name UNIQUE;
DEFINE INDEX idx_industry_wikidata ON TABLE industry COLUMNS wikidata_id;

-- Companies
DEFINE TABLE company SCHEMAFULL;
DEFINE FIELD name ON TABLE company TYPE string;
DEFINE FIELD ticker ON TABLE company TYPE option<string>;
DEFINE FIELD description ON TABLE company TYPE option<string>;
-- Price
DEFINE FIELD current_price ON TABLE company TYPE option<float>;
DEFINE FIELD currency ON TABLE company TYPE option<string>;
-- Market & revenue
DEFINE FIELD market_cap ON TABLE company TYPE option<float>;
DEFINE FIELD revenue ON TABLE company TYPE option<float>;
-- Earnings & valuation
DEFINE FIELD earnings ON TABLE company TYPE option<float>;
DEFINE FIELD trailing_eps ON TABLE company TYPE option<float>;
DEFINE FIELD forward_eps ON TABLE company TYPE option<float>;
DEFINE FIELD trailing_pe ON TABLE company TYPE option<float>;
DEFINE FIELD forward_pe ON TABLE company TYPE option<float>;
DEFINE FIELD peg_ratio ON TABLE company TYPE option<float>;
DEFINE FIELD price_to_book ON TABLE company TYPE option<float>;
DEFINE FIELD price_to_sales ON TABLE company TYPE option<float>;
-- Margins
DEFINE FIELD gross_margin ON TABLE company TYPE option<float>;
DEFINE FIELD operating_margin ON TABLE company TYPE option<float>;
DEFINE FIELD profit_margin ON TABLE company TYPE option<float>;
DEFINE FIELD cost_of_revenue ON TABLE company TYPE option<float>;
-- Cash flow & balance sheet
DEFINE FIELD ebitda ON TABLE company TYPE option<float>;
DEFINE FIELD free_cash_flow ON TABLE company TYPE option<float>;
DEFINE FIELD operating_cash_flow ON TABLE company TYPE option<float>;
DEFINE FIELD total_cash ON TABLE company TYPE option<float>;
DEFINE FIELD total_debt ON TABLE company TYPE option<float>;
DEFINE FIELD debt_to_equity ON TABLE company TYPE option<float>;
-- Growth & risk
DEFINE FIELD revenue_growth ON TABLE company TYPE option<float>;
DEFINE FIELD earnings_growth ON TABLE company TYPE option<float>;
DEFINE FIELD beta ON TABLE company TYPE option<float>;
-- Dividends
DEFINE FIELD dividend_yield ON TABLE company TYPE option<float>;
DEFINE FIELD dividend_rate ON TABLE company TYPE option<float>;
-- Meta
DEFINE FIELD employees ON TABLE company TYPE option<int>;
DEFINE FIELD hq_country ON TABLE company TYPE option<string>;
DEFINE FIELD hq_city ON TABLE company TYPE option<string>;
DEFINE FIELD founded ON TABLE company TYPE option<string>;
DEFINE FIELD website ON TABLE company TYPE option<string>;
DEFINE FIELD wikidata_id ON TABLE company TYPE option<string>;
DEFINE FIELD yfinance_industry ON TABLE company TYPE option<string>;
DEFINE FIELD yfinance_sector ON TABLE company TYPE option<string>;
DEFINE FIELD source ON TABLE company TYPE option<string>;
DEFINE FIELD status ON TABLE company TYPE option<string>; -- stub, processed
DEFINE FIELD created_at ON TABLE company TYPE datetime VALUE time::now();
DEFINE FIELD updated_at ON TABLE company TYPE option<datetime> VALUE time::now();
DEFINE INDEX idx_company_name ON TABLE company COLUMNS name UNIQUE;
DEFINE INDEX idx_company_ticker ON TABLE company COLUMNS ticker;

-- Technologies
DEFINE TABLE technology SCHEMAFULL;
DEFINE FIELD name ON TABLE technology TYPE string;
DEFINE FIELD description ON TABLE technology TYPE option<string>;
DEFINE FIELD maturity ON TABLE technology TYPE option<string>; -- emerging, growing, mature, declining
DEFINE FIELD adoption_stage ON TABLE technology TYPE option<string>; -- r&d, early_adopter, mainstream, legacy
DEFINE FIELD source ON TABLE technology TYPE option<string>;
DEFINE FIELD created_at ON TABLE technology TYPE datetime VALUE time::now();
DEFINE FIELD updated_at ON TABLE technology TYPE option<datetime> VALUE time::now();
DEFINE INDEX idx_tech_name ON TABLE technology COLUMNS name UNIQUE;

-- Products / Services
DEFINE TABLE product SCHEMAFULL;
DEFINE FIELD name ON TABLE product TYPE string;
DEFINE FIELD description ON TABLE product TYPE option<string>;
DEFINE FIELD category ON TABLE product TYPE option<string>;
DEFINE FIELD source ON TABLE product TYPE option<string>;
DEFINE FIELD created_at ON TABLE product TYPE datetime VALUE time::now();
DEFINE FIELD updated_at ON TABLE product TYPE option<datetime> VALUE time::now();
DEFINE INDEX idx_product_name ON TABLE product COLUMNS name;

-- Commodities / Raw Inputs
DEFINE TABLE commodity SCHEMAFULL;
DEFINE FIELD name ON TABLE commodity TYPE string;
DEFINE FIELD description ON TABLE commodity TYPE option<string>;
DEFINE FIELD wikidata_id ON TABLE commodity TYPE option<string>;
DEFINE FIELD category ON TABLE commodity TYPE option<string>; -- metal, energy, agricultural, chemical
DEFINE FIELD unit ON TABLE commodity TYPE option<string>;
DEFINE FIELD current_price ON TABLE commodity TYPE option<float>;
DEFINE FIELD volatility ON TABLE commodity TYPE option<float>;
DEFINE FIELD source ON TABLE commodity TYPE option<string>;
DEFINE FIELD status ON TABLE commodity TYPE option<string>; -- stub, processed
DEFINE FIELD created_at ON TABLE commodity TYPE datetime VALUE time::now();
DEFINE FIELD updated_at ON TABLE commodity TYPE option<datetime> VALUE time::now();
DEFINE INDEX idx_commodity_name ON TABLE commodity COLUMNS name UNIQUE;

-- Government Policies / Subsidies
DEFINE TABLE policy SCHEMAFULL;
DEFINE FIELD name ON TABLE policy TYPE string;
DEFINE FIELD description ON TABLE policy TYPE option<string>;
DEFINE FIELD policy_type ON TABLE policy TYPE option<string>; -- subsidy, tariff, regulation, tax_credit, ban
DEFINE FIELD region ON TABLE policy TYPE option<string>;
DEFINE FIELD status ON TABLE policy TYPE option<string>; -- proposed, active, expired
DEFINE FIELD effective_date ON TABLE policy TYPE option<string>;
DEFINE FIELD source ON TABLE policy TYPE option<string>;
DEFINE FIELD created_at ON TABLE policy TYPE datetime VALUE time::now();
DEFINE FIELD updated_at ON TABLE policy TYPE option<datetime> VALUE time::now();
DEFINE INDEX idx_policy_name ON TABLE policy COLUMNS name UNIQUE;

-- Events / Shocks (including Polymarket events)
DEFINE TABLE event SCHEMAFULL;
DEFINE FIELD name ON TABLE event TYPE string;
DEFINE FIELD description ON TABLE event TYPE option<string>;
DEFINE FIELD event_type ON TABLE event TYPE option<string>; -- market_shock, geopolitical, technology_shift, regulation
DEFINE FIELD polymarket_id ON TABLE event TYPE option<string>;
DEFINE FIELD probability ON TABLE event TYPE option<float>; -- 0-1 from Polymarket
DEFINE FIELD timeframe ON TABLE event TYPE option<string>;
DEFINE FIELD source ON TABLE event TYPE option<string>;
DEFINE FIELD created_at ON TABLE event TYPE datetime VALUE time::now();
DEFINE FIELD updated_at ON TABLE event TYPE option<datetime> VALUE time::now();
DEFINE INDEX idx_event_name ON TABLE event COLUMNS name;

-- ============================================================
-- EDGE TABLES (Relationships)
-- ============================================================

-- Company operates in an industry
DEFINE TABLE operates_in TYPE RELATION IN company OUT industry;
DEFINE FIELD market_share ON TABLE operates_in TYPE option<float>;
DEFINE FIELD revenue_pct ON TABLE operates_in TYPE option<float>;
DEFINE FIELD role ON TABLE operates_in TYPE option<string>; -- leader, challenger, niche, new_entrant
DEFINE FIELD confidence ON TABLE operates_in TYPE option<float>;
DEFINE FIELD source ON TABLE operates_in TYPE option<string>;

-- Company competes with company
DEFINE TABLE competes_with TYPE RELATION IN company OUT company;
DEFINE FIELD overlap_score ON TABLE competes_with TYPE option<float>;
DEFINE FIELD segments ON TABLE competes_with TYPE option<array<string>>;
DEFINE FIELD confidence ON TABLE competes_with TYPE option<float>;
DEFINE FIELD source ON TABLE competes_with TYPE option<string>;

-- Company supplies to company
DEFINE TABLE supplies_to TYPE RELATION IN company OUT company;
DEFINE FIELD products ON TABLE supplies_to TYPE option<array<string>>;
DEFINE FIELD revenue_dependency ON TABLE supplies_to TYPE option<float>;
DEFINE FIELD criticality ON TABLE supplies_to TYPE option<string>; -- critical, important, minor
DEFINE FIELD confidence ON TABLE supplies_to TYPE option<float>;
DEFINE FIELD source ON TABLE supplies_to TYPE option<string>;

-- Complement relationship (companies/products that grow together)
DEFINE TABLE complement_of TYPE RELATION IN company OUT company;
DEFINE FIELD reason ON TABLE complement_of TYPE option<string>;
DEFINE FIELD correlation ON TABLE complement_of TYPE option<float>;
DEFINE FIELD confidence ON TABLE complement_of TYPE option<float>;
DEFINE FIELD source ON TABLE complement_of TYPE option<string>;

-- Substitute relationship (companies/products that replace each other)
DEFINE TABLE substitute_for TYPE RELATION IN company OUT company;
DEFINE FIELD substitutability ON TABLE substitute_for TYPE option<float>;
DEFINE FIELD switching_cost ON TABLE substitute_for TYPE option<string>; -- low, medium, high
DEFINE FIELD confidence ON TABLE substitute_for TYPE option<float>;
DEFINE FIELD source ON TABLE substitute_for TYPE option<string>;

-- Subsidiary / ownership
DEFINE TABLE subsidiary_of TYPE RELATION IN company OUT company;
DEFINE FIELD ownership_pct ON TABLE subsidiary_of TYPE option<float>;
DEFINE FIELD acquired_date ON TABLE subsidiary_of TYPE option<string>;
DEFINE FIELD confidence ON TABLE subsidiary_of TYPE option<float>;
DEFINE FIELD source ON TABLE subsidiary_of TYPE option<string>;

-- Company uses technology
DEFINE TABLE uses_technology TYPE RELATION IN company OUT technology;
DEFINE FIELD criticality ON TABLE uses_technology TYPE option<string>;
DEFINE FIELD adoption_date ON TABLE uses_technology TYPE option<string>;
DEFINE FIELD confidence ON TABLE uses_technology TYPE option<float>;
DEFINE FIELD source ON TABLE uses_technology TYPE option<string>;

-- Company invested in company/technology
DEFINE TABLE invested_in TYPE RELATION IN company OUT company;
DEFINE FIELD amount ON TABLE invested_in TYPE option<float>;
DEFINE FIELD date ON TABLE invested_in TYPE option<string>;
DEFINE FIELD round ON TABLE invested_in TYPE option<string>;
DEFINE FIELD confidence ON TABLE invested_in TYPE option<float>;
DEFINE FIELD source ON TABLE invested_in TYPE option<string>;

-- Company uses commodity input
DEFINE TABLE uses_input TYPE RELATION IN company OUT commodity;
DEFINE FIELD cost_sensitivity ON TABLE uses_input TYPE option<float>; -- 0-1 how much price matters
DEFINE FIELD annual_volume ON TABLE uses_input TYPE option<string>;
DEFINE FIELD pct_of_costs ON TABLE uses_input TYPE option<float>;
DEFINE FIELD confidence ON TABLE uses_input TYPE option<float>;
DEFINE FIELD source ON TABLE uses_input TYPE option<string>;

-- Industry uses commodity input (industry-level dependency)
DEFINE TABLE industry_uses_input TYPE RELATION IN industry OUT commodity;
DEFINE FIELD pct_of_industry_costs ON TABLE industry_uses_input TYPE option<float>;
DEFINE FIELD criticality ON TABLE industry_uses_input TYPE option<string>; -- critical, important, minor
DEFINE FIELD substitutability ON TABLE industry_uses_input TYPE option<string>; -- none, limited, moderate, high
DEFINE FIELD source ON TABLE industry_uses_input TYPE option<string>;

-- Commodity can substitute for another commodity
DEFINE TABLE substitute_input TYPE RELATION IN commodity OUT commodity;
DEFINE FIELD feasibility ON TABLE substitute_input TYPE option<string>; -- easy, moderate, difficult
DEFINE FIELD cost_premium ON TABLE substitute_input TYPE option<float>;
DEFINE FIELD confidence ON TABLE substitute_input TYPE option<float>;
DEFINE FIELD source ON TABLE substitute_input TYPE option<string>;

-- Event/shock drives demand for something
DEFINE TABLE demand_driver TYPE RELATION IN event OUT industry;
DEFINE FIELD direction ON TABLE demand_driver TYPE option<string>; -- increase, decrease
DEFINE FIELD magnitude ON TABLE demand_driver TYPE option<string>; -- low, medium, high
DEFINE FIELD confidence ON TABLE demand_driver TYPE option<float>;
DEFINE FIELD source ON TABLE demand_driver TYPE option<string>;

-- Policy affects company/industry
DEFINE TABLE affected_by_policy TYPE RELATION IN company OUT policy;
DEFINE FIELD impact_direction ON TABLE affected_by_policy TYPE option<string>; -- positive, negative
DEFINE FIELD magnitude ON TABLE affected_by_policy TYPE option<string>;
DEFINE FIELD mechanism ON TABLE affected_by_policy TYPE option<string>;
DEFINE FIELD confidence ON TABLE affected_by_policy TYPE option<float>;
DEFINE FIELD source ON TABLE affected_by_policy TYPE option<string>;

-- Company produces product (in a specific industry)
DEFINE TABLE produces TYPE RELATION IN company OUT product;
DEFINE FIELD significance ON TABLE produces TYPE option<string>; -- primary, major, minor, experimental
DEFINE FIELD industry ON TABLE produces TYPE option<string>; -- which industry this product sits in
DEFINE FIELD confidence ON TABLE produces TYPE option<float>;
DEFINE FIELD source ON TABLE produces TYPE option<string>;

-- Product belongs to industry
DEFINE TABLE product_in_industry TYPE RELATION IN product OUT industry;
DEFINE FIELD market_share ON TABLE product_in_industry TYPE option<float>;
DEFINE FIELD source ON TABLE product_in_industry TYPE option<string>;

-- ============================================================
-- USEFUL GRAPH QUERIES (for reference)
-- ============================================================

-- Find all companies in an industry:
-- SELECT <-operates_in<-company FROM industry WHERE name = "Electric Vehicles";

-- Find competitors of a company:
-- SELECT ->competes_with->company FROM company WHERE name = "Tesla";

-- Find supply chain (who supplies whom):
-- SELECT ->supplies_to->company FROM company WHERE name = "TSMC";

-- 2-hop shock propagation: event → industry → companies
-- SELECT ->demand_driver->industry<-operates_in<-company FROM event WHERE name = "AI Boom";

-- 3-hop: event → industry → companies → their commodity inputs
-- SELECT ->demand_driver->industry<-operates_in<-company->uses_input->commodity FROM event WHERE name = "AI Boom";

-- Find all relationships for a company (ego graph):
-- SELECT *, ->operates_in->industry, ->competes_with->company, ->supplies_to->company, ->uses_input->commodity FROM company WHERE name = "Tesla";
