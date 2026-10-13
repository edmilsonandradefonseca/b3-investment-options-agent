"""Explicit field semantics: unknown fields never become currency by substring."""

FRACTIONS = frozenset({"revenueGrowth", "earningsGrowth", "earningsGrowthAnnual", "grossMargins", "profitMargins", "operatingMargins", "returnOnEquity", "returnOnAssets", "trailingAnnualDividendYield"})
MULTIPLES = frozenset({"currentRatio", "quickRatio", "priceEarnings", "trailingPE", "forwardPE", "priceToBook", "enterpriseToRevenue", "enterpriseToEbitda"})
MONEY = frozenset({"marketCap", "enterpriseValue", "totalRevenue", "ebitda", "grossProfits", "netIncomeToCommon", "netIncome", "totalCash", "totalDebt", "freeCashflow", "operatingCashflow", "totalAssets", "totalLiabilities", "totalStockholderEquity"})
PER_SHARE = frozenset({"earningsPerShare", "trailingEps", "forwardEps", "revenuePerShare", "totalCashPerShare", "bookValue", "dividendRate", "trailingAnnualDividendRate"})


def fundamental_unit(field: str, currency=None) -> str | None:
    if field in FRACTIONS:
        return "fraction"
    if field in MULTIPLES:
        return "ratio"
    if field == "debtToEquity":
        return "percent"
    if field in MONEY:
        return str(currency or "BRL")
    if field in PER_SHARE:
        return str(currency or "BRL") + "/share"
    return None
