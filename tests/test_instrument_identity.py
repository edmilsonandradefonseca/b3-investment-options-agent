from datetime import date

from b3_agent.portfolio.capital_risk import CapitalRiskEngine
from b3_agent.portfolio.instrument_identity import InstrumentIdentityResolver
from b3_agent.portfolio.intelligence import PositionIntelligenceEngine
from b3_agent.schemas.position import PortfolioContext, Position


def _portfolio():
    return PortfolioContext(
        as_of=date(2026, 9, 27),
        positions=(
            Position("stock-petr", "PETR4", "STOCK", 2000, market_value=65000),
            Position(
                "call-petr", "PETRJ400", "OPTION", -2000,
                strike=40, expiration_date=date(2026, 10, 16),
                option_type="CALL", underlying_ticker="PETRPN",
                market_value=-1200,
            ),
            Position("stock-bbdc", "BBDC4", "STOCK", 1000, market_value=18000),
            Position(
                "call-bbdc", "BBDCJ200", "OPTION", -1000,
                strike=20, expiration_date=date(2026, 10, 16),
                option_type="CALL", underlying_ticker="BRADPN",
                market_value=-500,
            ),
        ),
    )


def test_btg_aliases_resolve_only_for_economic_aggregation():
    resolver = InstrumentIdentityResolver()
    assert resolver.resolve("PETRPN") == "PETR4"
    assert resolver.resolve("GGBRPN") == "GGBR4"
    assert resolver.resolve("BRADPN") == "BBDC4"
    assert resolver.resolve("CMIGPN") == "CMIG4"
    assert resolver.resolve("ITUB4") == "ITUB4"


def test_exposure_groups_btg_reference_alias_with_stock_without_mutating_source():
    portfolio = _portfolio()
    exposures = PositionIntelligenceEngine().build_exposures(portfolio)
    by_ticker = {item.ticker: item for item in exposures}
    assert set(by_ticker) == {"BBDC4", "PETR4"}
    assert by_ticker["PETR4"].option_count == 1
    assert by_ticker["PETR4"].call_coverage_ratio == 1.0
    assert by_ticker["BBDC4"].call_coverage_ratio == 1.0
    assert portfolio.positions[1].underlying_ticker == "PETRPN"
    assert portfolio.positions[3].underlying_ticker == "BRADPN"


def test_capital_risk_uses_same_identity_resolution_for_call_coverage():
    result = CapitalRiskEngine().assess(_portfolio())
    assert result.uncovered_call_shares == 0.0
