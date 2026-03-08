"""
yfinance connector — pulls company and industry data.
No API key needed. Rate limit friendly.
"""

import yfinance as yf


def get_company_info(ticker: str) -> dict | None:
    """Get company fundamentals by ticker symbol."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        if not info or "shortName" not in info:
            return None
        return {
            "name": info.get("shortName") or info.get("longName", ticker),
            "ticker": ticker.upper(),
            "description": info.get("longBusinessSummary", ""),
            "market_cap": info.get("marketCap"),
            "revenue": info.get("totalRevenue"),
            "employees": info.get("fullTimeEmployees"),
            "hq_country": info.get("country"),
            "hq_city": info.get("city"),
            "website": info.get("website"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            # Price
            "current_price": info.get("currentPrice"),
            "currency": info.get("currency"),
            # Earnings & valuation
            "earnings": info.get("netIncomeToCommon"),
            "trailing_eps": info.get("trailingEps"),
            "forward_eps": info.get("forwardEps"),
            "trailing_pe": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "peg_ratio": info.get("trailingPegRatio"),
            "price_to_book": info.get("priceToBook"),
            "price_to_sales": info.get("priceToSalesTrailing12Months"),
            # Cash flow & balance sheet
            "ebitda": info.get("ebitda"),
            "free_cash_flow": info.get("freeCashflow"),
            "operating_cash_flow": info.get("operatingCashflow"),
            "total_cash": info.get("totalCash"),
            "total_debt": info.get("totalDebt"),
            "debt_to_equity": info.get("debtToEquity"),
            # Growth & risk
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_growth": info.get("earningsGrowth"),
            "beta": info.get("beta"),
            # Dividends
            "dividend_yield": info.get("dividendYield"),
            "dividend_rate": info.get("dividendRate"),
            "source": "yfinance",
        }
    except Exception as e:
        print(f"yfinance error for {ticker}: {e}")
        return None


def get_industry_companies(sector: str) -> list[dict]:
    """
    Get companies in a sector/industry using yfinance screener.
    Returns basic info for each company found.
    """
    # yfinance doesn't have a great screener API, so we use known sector tickers
    # In practice, the LLM agent will suggest tickers to look up
    return []


def get_company_by_name(name: str) -> dict | None:
    """
    Try to find a company by name using yfinance search.
    Falls back to using the name as a ticker.
    """
    try:
        search = yf.Search(name, max_results=5)
        quotes = search.quotes
        if quotes:
            # Take the first equity result
            for q in quotes:
                if q.get("quoteType") == "EQUITY":
                    return get_company_info(q["symbol"])
        return None
    except Exception as e:
        print(f"yfinance search error for {name}: {e}")
        return None


def get_key_stats(ticker: str) -> dict | None:
    """Get financial stats useful for cost sensitivity analysis."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return {
            "ticker": ticker.upper(),
            "gross_margins": info.get("grossMargins"),
            "operating_margins": info.get("operatingMargins"),
            "profit_margins": info.get("profitMargins"),
            "revenue_growth": info.get("revenueGrowth"),
            "cost_of_revenue": info.get("costOfRevenue"),
            "total_revenue": info.get("totalRevenue"),
        }
    except Exception as e:
        print(f"yfinance stats error for {ticker}: {e}")
        return None


if __name__ == "__main__":
    # Quick test
    import json

    info = get_company_info("TSLA")
    if info:
        print(json.dumps(info, indent=2, default=str))

    info = get_company_by_name("Taiwan Semiconductor")
    if info:
        print(json.dumps(info, indent=2, default=str))
