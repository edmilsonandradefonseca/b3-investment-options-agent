from __future__ import annotations

from dataclasses import replace

from datetime import date, datetime, timedelta, timezone

from b3_agent.schemas.fundamental import StockFundamental
from b3_agent.schemas.market import StockMarketData
from b3_agent.schemas.option import OptionContract, OptionQuote
from b3_agent.schemas.position import PortfolioContext, Position
from b3_agent.strategy_live import LiveStrategyComparisonService, StrategyEvidenceService


class FakeMarketProvider:
    name = "fake-market"

    def get_market_data(self, ticker, start, end):
        observed = datetime(2026, 7, 1, tzinfo=timezone.utc)
        rows = []
        base = 50.0 if ticker == "VALE3" else 30.0
        for index in range(70):
            price = base + index * 0.2
            rows.append(
                StockMarketData(
                    instrument_id=ticker,
                    ticker=ticker,
                    observation_timestamp=observed + timedelta(days=index),
                    available_timestamp=observed + timedelta(days=index, hours=1),
                    source=self.name,
                    ingested_at=observed + timedelta(days=index, hours=1),
                    source_record_id=f"{ticker}:{index}",
                    open=price - 0.1,
                    high=price + 0.3,
                    low=price - 0.2,
                    close=price,
                    volume=1_000_000 + index,
                )
            )
        return rows


class FakeCurrentQuoteProvider:
    name = "oplab"

    def get_current_quote(self, ticker):
        ts = datetime(2026, 10, 1, 15, 59, tzinfo=timezone.utc)
        price = 69.74 if ticker == "VALE3" else 49.74
        return StockMarketData(
            instrument_id=ticker,
            ticker=ticker,
            observation_timestamp=ts,
            available_timestamp=ts,
            source=self.name,
            ingested_at=ts,
            source_record_id=f"{ticker}:current",
            quality_flags=("current_quote",),
            open=price,
            high=price,
            low=price,
            close=price,
            volume=2_000_000,
        )


class FakeOptionsProvider:
    name = "oplab"

    def get_snapshot(self, ticker, as_of):
        put_contract = OptionContract(
            option_id="WEGEV500",
            underlying_id="WEGE3",
            underlying_ticker="WEGE3",
            option_ticker="WEGEV500",
            option_type="PUT",
            strike=50.0,
            expiration_date=date(2026, 11, 20),
            exercise_style="AMERICAN",
            contract_multiplier=100.0,
        )
        second_put_contract = OptionContract(
            option_id="WEGEV490",
            underlying_id="WEGE3",
            underlying_ticker="WEGE3",
            option_ticker="WEGEV490",
            option_type="PUT",
            strike=49.0,
            expiration_date=date(2026, 11, 20),
            exercise_style="EUROPEAN",
            contract_multiplier=100.0,
        )
        call_contract = OptionContract(
            option_id="WEGEJ550",
            underlying_id="WEGE3",
            underlying_ticker="WEGE3",
            option_ticker="WEGEJ550",
            option_type="CALL",
            strike=55.0,
            expiration_date=date(2026, 11, 20),
            contract_multiplier=100.0,
        )
        put_quote = OptionQuote(
            instrument_id="WEGEV500",
            ticker="WEGE3",
            observation_timestamp=as_of,
            available_timestamp=as_of,
            source=self.name,
            ingested_at=as_of,
            source_record_id="WEGE3:WEGEV500:current",
            option_id="WEGEV500",
            bid=1.20,
            ask=1.40,
            last=1.30,
            mid=1.30,
            volume=1500,
            open_interest=3000,
            implied_volatility=0.30,
            delta=-0.48,
        )
        second_put_quote = OptionQuote(
            instrument_id="WEGEV490",
            ticker="WEGE3",
            observation_timestamp=as_of,
            available_timestamp=as_of,
            source=self.name,
            ingested_at=as_of,
            source_record_id="WEGE3:WEGEV490:current",
            option_id="WEGEV490",
            bid=0.60,
            ask=0.80,
            last=0.70,
            mid=0.70,
            volume=700,
            open_interest=1100,
            implied_volatility=0.32,
            delta=-0.39,
        )
        call_quote = OptionQuote(
            instrument_id="WEGEJ550",
            ticker="WEGE3",
            observation_timestamp=as_of,
            available_timestamp=as_of,
            source=self.name,
            ingested_at=as_of,
            source_record_id="WEGE3:WEGEJ550:current",
            option_id="WEGEJ550",
            bid=0.80,
            ask=0.90,
            last=0.85,
            mid=0.85,
            volume=900,
            open_interest=1500,
        )
        return [put_contract, second_put_contract, call_contract], [put_quote, second_put_quote, call_quote]


class FakeFundamentalsProvider:
    name = "fake-fundamentals"

    def get_financial_data(self, ticker):
        ts = datetime(2026, 9, 30, tzinfo=timezone.utc)
        return [
            StockFundamental(
                instrument_id=ticker,
                ticker=ticker,
                observation_timestamp=ts,
                available_timestamp=ts,
                source=self.name,
                ingested_at=ts,
                source_record_id=f"{ticker}:eps",
                quality_status="WARNING",
                quality_flags=("availability_is_ingestion_time",),
                metric="earningsPerShare",
                value=4.2 if ticker == "VALE3" else 1.8,
                report_date=date(2026, 9, 30),
                period_type="TTM",
                unit="BRL/share",
            )
        ]


def _portfolio():
    return PortfolioContext(
        as_of=date(2026, 9, 27),
        cash=0.0,
        cash_is_known=False,
        positions=(
            Position(
                position_id="PETR4-STOCK",
                ticker="PETR4",
                instrument_type="STOCK",
                quantity=100,
                market_price=40.0,
                market_value=4000.0,
            ),
        ),
        source_refs=("BTG",),
    )


def test_live_strategy_comparison_builds_two_asset_evidence_packs_without_ranking():
    evidence = StrategyEvidenceService(
        market_provider=FakeMarketProvider(),
        fundamentals_provider=FakeFundamentalsProvider(),
        current_quote_provider=FakeCurrentQuoteProvider(),
        history_days=120,
    )
    service = LiveStrategyComparisonService(evidence_service=evidence)
    as_of = datetime(2026, 10, 1, 15, 0, tzinfo=timezone.utc)

    result = service.compare(
        assets=("VALE3", "WEGE3"),
        strategies=("Comprar ação", "Comprar ação"),
        amount=50_000.0,
        portfolio=_portfolio(),
        as_of=as_of,
    )

    assert set(result["asset_evidence"]) == {"VALE3", "WEGE3"}
    assert result["asset_evidence"]["VALE3"]["market"]["history_count"] == 70
    assert result["asset_evidence"]["VALE3"]["market"]["current_quote"]["close"] == 69.74
    assert result["asset_evidence"]["WEGE3"]["market"]["current_quote"]["close"] == 49.74
    assert result["asset_evidence"]["VALE3"]["fundamentals"]["metric_count"] == 1
    assert result["asset_evidence"]["VALE3"]["portfolio"]["held"] is False
    assert result["strategy_comparison"]["alternatives"][0]["capital_required"] == 50_000.0
    assert result["strategy_comparison"]["alternatives"][1]["capital_required"] == 50_000.0
    assert result["strategy_comparison"]["assumptions"]["ranking"] == "not_applied"
    assert result["quality_status"] == "WARNING"
    assert "PETR4" not in str(result["asset_evidence"])


def test_invalid_b3_ticker_is_rejected_before_any_provider_call():
    calls = []

    class RecordingMarketProvider(FakeMarketProvider):
        def get_market_data(self, ticker, start, end):
            calls.append(("market", ticker))
            return super().get_market_data(ticker, start, end)

    evidence = StrategyEvidenceService(
        market_provider=RecordingMarketProvider(),
        fundamentals_provider=FakeFundamentalsProvider(),
        current_quote_provider=FakeCurrentQuoteProvider(),
    )
    service = LiveStrategyComparisonService(evidence_service=evidence)

    try:
        service.compare(
            assets=("ITUB4", "WWEGE3"),
            strategies=("Comprar ação", "Comprar ação"),
            as_of=datetime(2026, 10, 1, 15, 0, tzinfo=timezone.utc),
        )
    except ValueError as exc:
        assert "invalid B3 equity ticker 'WWEGE3'" in str(exc)
    else:
        raise AssertionError("invalid ticker was sent to data providers")

    assert calls == []


def test_sell_put_requires_explicit_contract():
    evidence = StrategyEvidenceService(
        market_provider=FakeMarketProvider(),
        fundamentals_provider=FakeFundamentalsProvider(),
        current_quote_provider=FakeCurrentQuoteProvider(),
    )
    service = LiveStrategyComparisonService(
        evidence_service=evidence,
        options_provider=FakeOptionsProvider(),
    )

    try:
        service.compare(
            assets=("VALE3", "WEGE3"),
            strategies=("Comprar ação", "Vender PUT"),
            portfolio=_portfolio(),
            as_of=datetime(2026, 10, 1, tzinfo=timezone.utc),
        )
    except ValueError as exc:
        assert "explicit current OPLAB option identifier" in str(exc)
    else:
        raise AssertionError("SELL_PUT must require an explicit contract")


def test_sell_put_uses_current_oplab_bid_and_one_cash_secured_contract():
    evidence = StrategyEvidenceService(
        market_provider=FakeMarketProvider(),
        fundamentals_provider=FakeFundamentalsProvider(),
        current_quote_provider=FakeCurrentQuoteProvider(),
    )
    service = LiveStrategyComparisonService(
        evidence_service=evidence,
        options_provider=FakeOptionsProvider(),
    )
    as_of = datetime(2026, 10, 1, 15, 0, tzinfo=timezone.utc)

    result = service.compare(
        assets=("VALE3", "WEGE3"),
        strategies=("Comprar ação", "Vender PUT"),
        option_ids=(None, "WEGEV500"),
        amount=50_000.0,
        portfolio=_portfolio(),
        as_of=as_of,
    )

    alternative = result["strategy_comparison"]["alternatives"][1]
    assert alternative["action_type"] == "SELL_PUT"
    assert alternative["subject_id"] == "WEGEV500"
    assert alternative["capital_required"] == 5000.0
    assert alternative["max_loss"] == 4880.0
    assert alternative["assumptions"]["premium_basis"] == "current_bid"
    assert alternative["assumptions"]["current_option_quote"]["bid"] == 1.20
    assert result["option_evidence"]["WEGEV500"]["current_quote"]["last"] == 1.30


def test_multi_strike_put_comparison_keeps_probability_and_assignment_measures_separate():
    evidence = StrategyEvidenceService(
        market_provider=FakeMarketProvider(),
        fundamentals_provider=FakeFundamentalsProvider(),
        current_quote_provider=FakeCurrentQuoteProvider(),
    )
    result = LiveStrategyComparisonService(
        evidence_service=evidence,
        options_provider=FakeOptionsProvider(),
    ).compare_put_candidates(
        ticker="WEGE3",
        option_ids=("WEGEV500", "WEGEV490"),
        scenario_horizon="2026-11-20",
        scenario_shocks_pct=(-10, 0, 10),
        scenario_objective="MAXIMIZE_WORST_CASE_RETURN_ON_CAPITAL",
        portfolio=_portfolio(),
        as_of=datetime(2026, 10, 1, 16, 0, tzinfo=timezone.utc),
    )
    comparison = result["put_chain_comparison"]
    assert comparison["candidate_count"] == 2
    assert [row["contract"]["option_id"] for row in comparison["candidates"]] == ["WEGEV490", "WEGEV500"]
    low_strike, high_strike = comparison["candidates"]
    assert low_strike["premium_total_one_contract"] == 60.0
    assert low_strike["capital_required_one_contract"] == 4900.0
    assert low_strike["breakeven_price"] == 48.4
    assert low_strike["probability_estimates"]["expiry_itm_probability"] is not None
    assert low_strike["probability_estimates"]["touch_probability"] is not None
    assert low_strike["probability_estimates"]["expiry_itm_probability"] <= low_strike["probability_estimates"]["touch_probability"]
    assert low_strike["early_assignment"]["status"] == "NOT_APPLICABLE_BY_PROVIDER_REPORTED_EUROPEAN_STYLE"
    assert high_strike["early_assignment"]["status"] == "UNKNOWN"
    assert high_strike["personal_assignment_frequency"]["status"] == "UNKNOWN"
    assert high_strike["pnl_by_scenario_brl"]["2026-11-20:-10%"] == -403.4
    assert comparison["ranking"]["status"] in {"CONDITIONAL_RANKING", "TIE"}


def test_multi_strike_put_requires_exact_ids_and_same_expiration():
    evidence = StrategyEvidenceService(
        market_provider=FakeMarketProvider(),
        fundamentals_provider=FakeFundamentalsProvider(),
        current_quote_provider=FakeCurrentQuoteProvider(),
    )
    service = LiveStrategyComparisonService(evidence_service=evidence, options_provider=FakeOptionsProvider())
    try:
        service.compare_put_candidates(
            ticker="WEGE3", option_ids=("WEGEV500", "NOT-LISTED"),
            as_of=datetime(2026, 10, 1, tzinfo=timezone.utc),
        )
    except ValueError as exc:
        assert "exactly one current contract" in str(exc)
    else:
        raise AssertionError("an unlisted sibling must not be silently substituted")


def test_multi_strike_put_does_not_use_underlying_quote_after_requested_as_of():
    evidence = StrategyEvidenceService(
        market_provider=FakeMarketProvider(),
        fundamentals_provider=FakeFundamentalsProvider(),
        current_quote_provider=FakeCurrentQuoteProvider(),
    )
    service = LiveStrategyComparisonService(evidence_service=evidence, options_provider=FakeOptionsProvider())
    try:
        service.compare_put_candidates(
            ticker="WEGE3", option_ids=("WEGEV500", "WEGEV490"),
            as_of=datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc),
        )
    except ValueError as exc:
        assert "underlying quote was not observable" in str(exc)
    else:
        raise AssertionError("future quote availability must not enter a past as_of comparison")


def test_explicit_expiry_scenarios_calculate_stock_and_cash_secured_put_payoffs():
    evidence = StrategyEvidenceService(
        market_provider=FakeMarketProvider(),
        fundamentals_provider=FakeFundamentalsProvider(),
        current_quote_provider=FakeCurrentQuoteProvider(),
    )
    result = LiveStrategyComparisonService(
        evidence_service=evidence,
        options_provider=FakeOptionsProvider(),
    ).compare(
        assets=("VALE3", "WEGE3"),
        strategies=("Comprar ação", "Vender PUT"),
        option_ids=(None, "WEGEV500"),
        amount=5000.0,
        scenario_horizon="2026-11-20",
        scenario_shocks_pct=(-10, 0, 10),
        portfolio=_portfolio(),
        as_of=datetime(2026, 10, 1, 15, 0, tzinfo=timezone.utc),
    )

    scenarios = result["scenario_analysis"]
    assert scenarios["status"] == "COMPUTED"
    assert scenarios["probabilities"] is None
    left, right = scenarios["alternatives"]
    assert left["pnl_by_scenario_brl"]["2026-11-20:-10%"] == -500.0
    assert right["pnl_by_scenario_brl"]["2026-11-20:-10%"] == -403.4
    assert right["pnl_by_scenario_brl"]["2026-11-20:0%"] == 94.0
    assert abs(
        result["strategy_comparison"]["scenario_deltas"]["2026-11-20:-10%"] - 96.6
    ) < 1e-9
    assert result["scenario_analysis"]["objective_policy"]["status"] == "NOT_REQUESTED"


def test_explicit_objective_ranks_only_complete_scenario_returns_on_known_capital():
    evidence = StrategyEvidenceService(
        market_provider=FakeMarketProvider(),
        fundamentals_provider=FakeFundamentalsProvider(),
        current_quote_provider=FakeCurrentQuoteProvider(),
    )
    result = LiveStrategyComparisonService(
        evidence_service=evidence,
        options_provider=FakeOptionsProvider(),
    ).compare(
        assets=("VALE3", "WEGE3"),
        strategies=("Comprar ação", "Vender PUT"),
        option_ids=(None, "WEGEV500"),
        amount=5000.0,
        scenario_horizon="2026-11-20",
        scenario_shocks_pct=(-10, 0, 10),
        scenario_objective="MAXIMIZE_WORST_CASE_RETURN_ON_CAPITAL",
        portfolio=_portfolio(),
        as_of=datetime(2026, 10, 1, 15, 0, tzinfo=timezone.utc),
    )
    policy = result["scenario_analysis"]["objective_policy"]
    alternatives = result["scenario_analysis"]["alternatives"]
    assert policy["status"] == "CONDITIONAL_RANKING"
    assert policy["ranked_alternative_id"] == alternatives[1]["alternative_id"]
    assert alternatives[0]["capital_basis_brl"] == 5000.0
    assert alternatives[1]["capital_basis_brl"] == 5000.0
    assert policy["worst_case_return_pct_by_alternative"][alternatives[1]["alternative_id"]] > -10
    assert policy["not_a_forecast"] is True


def test_option_payoff_is_not_marked_at_a_non_expiry_horizon():
    evidence = StrategyEvidenceService(
        market_provider=FakeMarketProvider(),
        fundamentals_provider=FakeFundamentalsProvider(),
        current_quote_provider=FakeCurrentQuoteProvider(),
    )
    result = LiveStrategyComparisonService(
        evidence_service=evidence,
        options_provider=FakeOptionsProvider(),
    ).compare(
        assets=("VALE3", "WEGE3"),
        strategies=("Comprar ação", "Vender PUT"),
        option_ids=(None, "WEGEV500"),
        amount=5000.0,
        scenario_horizon="2026-11-06",
        scenario_shocks_pct=(-10, 10),
        portfolio=_portfolio(),
        as_of=datetime(2026, 10, 1, 15, 0, tzinfo=timezone.utc),
    )
    assert result["scenario_analysis"]["status"] == "PARTIAL"
    assert result["scenario_analysis"]["alternatives"][1]["pnl_by_scenario_brl"] == {}


def test_covered_call_scenario_includes_covered_share_change_and_bid_premium():
    evidence = StrategyEvidenceService(
        market_provider=FakeMarketProvider(),
        fundamentals_provider=FakeFundamentalsProvider(),
        current_quote_provider=FakeCurrentQuoteProvider(),
    )
    result = LiveStrategyComparisonService(
        evidence_service=evidence,
        options_provider=FakeOptionsProvider(),
    ).compare(
        assets=("VALE3", "WEGE3"),
        strategies=("Comprar ação", "Vender CALL coberta"),
        option_ids=(None, "WEGEJ550"),
        amount=5000.0,
        scenario_horizon="2026-11-20",
        scenario_shocks_pct=(10, 20),
        portfolio=_covered_portfolio(),
        as_of=datetime(2026, 10, 1, 15, 0, tzinfo=timezone.utc),
    )
    call_payoffs = result["scenario_analysis"]["alternatives"][1]["pnl_by_scenario_brl"]
    assert call_payoffs["2026-11-20:10%"] == 577.4
    assert call_payoffs["2026-11-20:20%"] == 606.0


def test_explicit_scenario_inputs_are_bounded_and_unique():
    evidence = StrategyEvidenceService(
        market_provider=FakeMarketProvider(),
        fundamentals_provider=FakeFundamentalsProvider(),
        current_quote_provider=FakeCurrentQuoteProvider(),
    )
    service = LiveStrategyComparisonService(evidence_service=evidence)
    for shocks in ((-10, -10), (float("nan"),), tuple(range(10))):
        try:
            service.compare(
                assets=("VALE3", "WEGE3"),
                strategies=("Comprar ação", "Comprar ação"),
                amount=5000.0,
                scenario_horizon="2026-11-20",
                scenario_shocks_pct=shocks,
                portfolio=_portfolio(),
                as_of=datetime(2026, 10, 1, 15, 0, tzinfo=timezone.utc),
            )
        except ValueError:
            pass
        else:
            raise AssertionError(f"invalid scenario shocks accepted: {shocks!r}")


def _covered_portfolio(shares: float = 100.0):
    return PortfolioContext(
        as_of=date(2026, 9, 27),
        cash=0.0,
        cash_is_known=False,
        positions=(
            Position(
                position_id="WEGE3-STOCK",
                ticker="WEGE3",
                instrument_type="STOCK",
                quantity=shares,
                market_price=49.74,
                market_value=49.74 * shares,
            ),
        ),
        source_refs=("BTG",),
    )


def test_sell_call_uses_current_bid_and_requires_covered_shares():
    evidence = StrategyEvidenceService(
        market_provider=FakeMarketProvider(),
        fundamentals_provider=FakeFundamentalsProvider(),
        current_quote_provider=FakeCurrentQuoteProvider(),
    )
    service = LiveStrategyComparisonService(
        evidence_service=evidence,
        options_provider=FakeOptionsProvider(),
    )
    as_of = datetime(2026, 10, 1, 15, 0, tzinfo=timezone.utc)

    result = service.compare(
        assets=("VALE3", "WEGE3"),
        strategies=("Comprar ação", "Vender CALL coberta"),
        option_ids=(None, "WEGEJ550"),
        amount=50_000.0,
        portfolio=_covered_portfolio(),
        as_of=as_of,
    )

    alternative = result["strategy_comparison"]["alternatives"][1]
    assert alternative["action_type"] == "SELL_CALL"
    assert alternative["subject_id"] == "WEGEJ550"
    assert alternative["capital_required"] == 0.0
    assert alternative["assumptions"]["covered_call"] is True
    assert alternative["assumptions"]["premium_basis"] == "current_bid"
    assert alternative["assumptions"]["covered_shares_required"] == 100.0
    assert alternative["assumptions"]["stock_shares_available"] == 100.0
    assert alternative["assumptions"]["covered_shares_already_committed"] == 0.0
    assert alternative["assumptions"]["covered_shares_free_before_trade"] == 100.0
    evidence_row = result["option_evidence"]["WEGEJ550"]
    assert evidence_row["current_quote"]["bid"] == 0.80
    assert evidence_row["call_analysis"]["premium"] == 0.80


def test_sell_call_rejects_uncovered_position():
    evidence = StrategyEvidenceService(
        market_provider=FakeMarketProvider(),
        fundamentals_provider=FakeFundamentalsProvider(),
        current_quote_provider=FakeCurrentQuoteProvider(),
    )
    service = LiveStrategyComparisonService(
        evidence_service=evidence,
        options_provider=FakeOptionsProvider(),
    )

    try:
        service.compare(
            assets=("VALE3", "WEGE3"),
            strategies=("Comprar ação", "Vender CALL coberta"),
            option_ids=(None, "WEGEJ550"),
            portfolio=_covered_portfolio(50.0),
            as_of=datetime(2026, 10, 1, 15, 0, tzinfo=timezone.utc),
        )
    except ValueError as exc:
        assert "not covered" in str(exc)
    else:
        raise AssertionError("SELL_CALL must reject insufficient underlying shares")


def test_sell_call_uses_only_uncommitted_shares_for_coverage():
    evidence = StrategyEvidenceService(
        market_provider=FakeMarketProvider(),
        fundamentals_provider=FakeFundamentalsProvider(),
        current_quote_provider=FakeCurrentQuoteProvider(),
    )
    service = LiveStrategyComparisonService(
        evidence_service=evidence,
        options_provider=FakeOptionsProvider(),
    )
    short_call = Position(
        position_id="WEGEJ500-OPEN", ticker="WEGEJ500", instrument_type="OPTION",
        quantity=-1, strike=50.0, expiration_date=date(2026, 11, 20),
        option_type="CALL", underlying_ticker="WEGE3", contract_multiplier=100.0,
        source_ref="BTG:open-call",
    )
    base = _covered_portfolio(200.0)
    portfolio = replace(base, positions=(*base.positions, short_call))
    result = service.compare(
        assets=("VALE3", "WEGE3"),
        strategies=("Comprar ação", "Vender CALL coberta"),
        option_ids=(None, "WEGEJ550"),
        amount=50_000.0,
        portfolio=portfolio,
        as_of=datetime(2026, 10, 1, 15, 0, tzinfo=timezone.utc),
    )
    assumptions = result["strategy_comparison"]["alternatives"][1]["assumptions"]
    assert assumptions["stock_shares_available"] == 200.0
    assert assumptions["covered_shares_already_committed"] == 100.0
    assert assumptions["covered_shares_free_before_trade"] == 100.0
    assert assumptions["existing_short_call_position_ids"] == ["WEGEJ500-OPEN"]


def test_sell_call_rejects_shares_already_committed_to_open_short_call():
    evidence = StrategyEvidenceService(
        market_provider=FakeMarketProvider(),
        fundamentals_provider=FakeFundamentalsProvider(),
        current_quote_provider=FakeCurrentQuoteProvider(),
    )
    service = LiveStrategyComparisonService(
        evidence_service=evidence,
        options_provider=FakeOptionsProvider(),
    )
    base = _covered_portfolio(100.0)
    short_call = Position(
        position_id="WEGEJ500-OPEN", ticker="WEGEJ500", instrument_type="OPTION",
        quantity=-1, strike=50.0, expiration_date=date(2026, 11, 20),
        option_type="CALL", underlying_ticker="WEGE3", contract_multiplier=100.0,
        source_ref="BTG:open-call",
    )
    portfolio = replace(base, positions=(*base.positions, short_call))
    try:
        service.compare(
            assets=("VALE3", "WEGE3"),
            strategies=("Comprar ação", "Vender CALL coberta"),
            option_ids=(None, "WEGEJ550"),
            portfolio=portfolio,
            as_of=datetime(2026, 10, 1, 15, 0, tzinfo=timezone.utc),
        )
    except ValueError as exc:
        assert "100 already committed" in str(exc)
    else:
        raise AssertionError("covered-call comparison reused shares already pledged to an open CALL")


def test_sell_stock_reduces_existing_long_position_as_notional_what_if():
    evidence = StrategyEvidenceService(
        market_provider=FakeMarketProvider(),
        fundamentals_provider=FakeFundamentalsProvider(),
        current_quote_provider=FakeCurrentQuoteProvider(),
    )
    service = LiveStrategyComparisonService(evidence_service=evidence)
    as_of = datetime(2026, 10, 1, 15, 0, tzinfo=timezone.utc)

    result = service.compare(
        assets=("WEGE3", "WEGE3"),
        strategies=("Manter", "Vender/reduzir ação"),
        amount=2000.0,
        portfolio=_covered_portfolio(),
        as_of=as_of,
    )

    alternative = result["strategy_comparison"]["alternatives"][1]
    assert alternative["action_type"] == "SELL_STOCK"
    assert alternative["capital_required"] == 0.0
    assumptions = alternative["assumptions"]
    assert assumptions["capital_released"] == 2000.0
    assert assumptions["stock_quantity_before"] == 100.0
    assert assumptions["theoretical_shares_reduced"] == 2000.0 / 49.74
    assert assumptions["stock_quantity_after_theoretical"] == (
        100.0 - 2000.0 / 49.74
    )
    assert assumptions["execution_quantity"] == "not_inferred"


def test_sell_stock_requires_existing_long_and_explicit_amount():
    evidence = StrategyEvidenceService(
        market_provider=FakeMarketProvider(),
        fundamentals_provider=FakeFundamentalsProvider(),
        current_quote_provider=FakeCurrentQuoteProvider(),
    )
    service = LiveStrategyComparisonService(evidence_service=evidence)

    try:
        service.compare(
            assets=("WEGE3", "WEGE3"),
            strategies=("Manter", "Vender/reduzir ação"),
            portfolio=_covered_portfolio(),
            as_of=datetime(2026, 10, 1, 15, 0, tzinfo=timezone.utc),
        )
    except ValueError as exc:
        assert "explicit positive comparison amount" in str(exc)
    else:
        raise AssertionError("SELL_STOCK must require explicit amount")

    try:
        service.compare(
            assets=("WEGE3", "WEGE3"),
            strategies=("Manter", "Vender/reduzir ação"),
            amount=6000.0,
            portfolio=_covered_portfolio(),
            as_of=datetime(2026, 10, 1, 15, 0, tzinfo=timezone.utc),
        )
    except ValueError as exc:
        assert "exceeds current long position value" in str(exc)
    else:
        raise AssertionError("SELL_STOCK must reject reduction above held value")

def test_interactive_evidence_freezes_after_acquisition_but_historical_cutoff_stays_fixed():
    from dataclasses import replace
    cutoff = datetime.now(timezone.utc)
    class NewlyAcquiredHistory(FakeMarketProvider):
        def get_market_data(self, ticker, start, end):
            acquired = datetime.now(timezone.utc)
            return [replace(row, available_timestamp=acquired, ingested_at=acquired)
                    for row in super().get_market_data(ticker,start,end)]
    service = StrategyEvidenceService(market_provider=NewlyAcquiredHistory(),
        fundamentals_provider=FakeFundamentalsProvider(), current_quote_provider=FakeCurrentQuoteProvider())
    historical = service.build('ITUB4',as_of=cutoff)
    interactive = service.build('ITUB4',as_of=cutoff,refresh_cutoff=True)
    assert historical.market['historical_returns']['1W']['status'] == 'INSUFFICIENT_HISTORY'
    assert historical.as_of == cutoff
    assert interactive.market['historical_returns']['1W']['status'] == 'AVAILABLE'
    assert interactive.as_of > cutoff
    assert interactive.market['price_history']
