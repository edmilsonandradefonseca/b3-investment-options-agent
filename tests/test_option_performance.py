from datetime import date

from b3_agent.options.lifecycle import OptionContract
from b3_agent.options.performance import OptionPerformanceEngine
from b3_agent.schemas.option_transaction import OptionTransaction


def tx(tid, ticker, qty, price, day):
    return OptionTransaction(
        transaction_id=tid,
        option_ticker=ticker,
        broker="BTG",
        quantity=qty,
        average_cost=price,
        total_cost=qty * price,
        as_of=date.fromisoformat(day),
    )


def test_short_put_performance_calculates_pnl_premium_and_return():
    rows = (
        tx("1", "EQTLV369", -1000, 0.64, "2026-09-11"),
        tx("2", "EQTLV369", 1000, 0.30, "2026-09-15"),
    )
    contract = OptionContract(
        option_ticker="EQTLV369",
        option_type="PUT",
        strike=36.9,
        underlying_ticker="EQTL3",
        contract_multiplier=1.0,
    )

    performance = OptionPerformanceEngine().build(rows, contracts={"EQTLV369": contract})

    assert len(performance) == 1
    item = performance[0]
    assert item.realized_pnl == 340.0
    assert item.premium_received == 640.0
    assert item.premium_paid == 300.0
    assert item.capital_basis == 36900.0
    assert item.return_pct == 0.9214
    assert item.return_basis == "CASH_SECURED_PUT_STRIKE_NOTIONAL"
    assert item.underlying_ticker == "EQTL3"


def test_underlying_aggregation_separates_put_and_call():
    rows = (
        tx("1", "EQTLV369", -1000, 0.64, "2026-09-11"),
        tx("2", "EQTLV369", 1000, 0.30, "2026-09-15"),
        tx("3", "EQTLW390", -1000, 0.50, "2026-09-12"),
        tx("4", "EQTLW390", 1000, 0.20, "2026-09-16"),
    )
    contracts = {
        "EQTLV369": OptionContract(
            option_ticker="EQTLV369",
            option_type="PUT",
            strike=36.9,
            underlying_ticker="EQTL3",
        ),
        "EQTLW390": OptionContract(
            option_ticker="EQTLW390",
            option_type="CALL",
            strike=39.0,
            underlying_ticker="EQTL3",
        ),
    }

    engine = OptionPerformanceEngine()
    performances = engine.build(rows, contracts=contracts)
    aggregate = engine.aggregate_by_underlying(performances)

    assert len(aggregate) == 1
    item = aggregate[0]
    assert item.underlying_ticker == "EQTL3"
    assert item.put_pnl == 340.0
    assert item.call_pnl == 300.0
    assert item.realized_pnl == 640.0
    assert item.premium_received == 1140.0
    assert item.premium_paid == 500.0


def test_call_return_is_not_claimed_without_stock_capital_basis():
    rows = (
        tx("1", "EQTLW390", -1000, 0.50, "2026-09-12"),
        tx("2", "EQTLW390", 1000, 0.20, "2026-09-16"),
    )
    contract = OptionContract(
        option_ticker="EQTLW390",
        option_type="CALL",
        strike=39.0,
        underlying_ticker="EQTL3",
    )

    performance = OptionPerformanceEngine().build(rows, contracts={"EQTLW390": contract})

    assert performance[0].realized_pnl == 300.0
    assert performance[0].return_pct is None
    assert performance[0].return_basis == "UNAVAILABLE"
