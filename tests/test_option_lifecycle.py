from datetime import date

from b3_agent.options.lifecycle import (
    OptionContract,
    OptionLifecycleEngine,
    build_option_lifecycles,
)
from b3_agent.schemas.option_transaction import OptionTransaction


def tx(tid, ticker, qty, price, day):
    return OptionTransaction(
        transaction_id=tid,
        option_ticker=ticker,
        broker="BTG Pactual",
        quantity=qty,
        average_cost=price,
        total_cost=qty * price,
        as_of=date.fromisoformat(day),
    )


def test_short_option_closes_and_calculates_realized_pnl_fifo():
    rows = (
        tx("1", "EQTLV369", -1000, 0.64, "2026-09-11"),
        tx("2", "EQTLV369", 400, 0.30, "2026-09-15"),
        tx("3", "EQTLV369", 600, 0.20, "2026-09-18"),
    )

    lifecycle = OptionLifecycleEngine().build(rows)

    assert lifecycle.status == "CLOSED"
    assert lifecycle.net_quantity == 0
    assert lifecycle.closed_quantity == 1000
    assert lifecycle.unmatched_quantity == 0
    assert lifecycle.realized_pnl == 400.0
    assert lifecycle.history_completeness == "COMPLETE"
    assert lifecycle.contract_metadata_quality == "MISSING"
    assert lifecycle.pnl_basis == "GROSS_UNIT_PRICE"


def test_partial_close_remains_open():
    rows = (
        tx("1", "PETRK376", -4500, 13.49, "2026-09-17"),
        tx("2", "PETRK376", 2000, 13.20, "2026-09-18"),
    )

    lifecycle = OptionLifecycleEngine().build(rows)

    assert lifecycle.status == "OPEN"
    assert lifecycle.net_quantity == -2500
    assert lifecycle.closed_quantity == 2000
    assert lifecycle.unmatched_quantity == 2500
    assert lifecycle.realized_pnl == 580.0
    assert lifecycle.history_completeness == "PARTIAL_OR_OPEN"


def test_expiration_without_outcome_is_not_assumed_worthless():
    rows = (
        tx("1", "ABCXX123", -1000, 0.50, "2026-09-10"),
    )
    contract = OptionContract(
        option_ticker="ABCXX123",
        expiration_date=date(2026, 9, 18),
        option_type="PUT",
        strike=10.0,
        underlying_ticker="ABC3",
    )

    lifecycle = OptionLifecycleEngine().build(
        rows,
        contract=contract,
        evaluation_date=date(2026, 9, 19),
    )

    assert lifecycle.status == "EXPIRED_UNRESOLVED"
    assert lifecycle.expiry_state == "EXPIRED_UNRESOLVED"
    assert lifecycle.net_quantity == -1000
    assert lifecycle.contract_metadata_quality == "COMPLETE"


def test_expiration_can_be_classified_explicitly():
    rows = (tx("1", "ABCXX123", -1000, 0.50, "2026-09-10"),)
    contract = OptionContract(
        option_ticker="ABCXX123",
        expiration_date=date(2026, 9, 18),
    )

    lifecycle = OptionLifecycleEngine().build(
        rows,
        contract=contract,
        evaluation_date=date(2026, 9, 19),
        expiry_outcome="WORTHLESS",
    )

    assert lifecycle.status == "EXPIRED_WORTHLESS"
    assert lifecycle.expiry_state == "WORTHLESS"
    assert lifecycle.net_quantity == -1000
    assert lifecycle.unmatched_quantity == 1000
    assert lifecycle.realized_pnl == 500.0
    assert lifecycle.contract_metadata_quality == "PARTIAL"


def test_build_option_lifecycles_groups_by_ticker():
    rows = (
        tx("1", "A", -100, 1.0, "2026-09-10"),
        tx("2", "A", 100, 0.5, "2026-09-11"),
        tx("3", "B", -200, 2.0, "2026-09-10"),
    )

    lifecycles = build_option_lifecycles(rows)

    assert [item.option_ticker for item in lifecycles] == ["A", "B"]
    assert lifecycles[0].status == "CLOSED"
    assert lifecycles[0].realized_pnl == 50.0
    assert lifecycles[1].status == "OPEN"


def test_long_option_expires_worthless_and_loses_premium():
    rows = (tx("1", "ABCXX124", 1000, 0.50, "2026-09-10"),)
    contract = OptionContract(
        option_ticker="ABCXX124",
        expiration_date=date(2026, 9, 18),
    )

    lifecycle = OptionLifecycleEngine().build(
        rows,
        contract=contract,
        evaluation_date=date(2026, 9, 19),
        expiry_outcome="WORTHLESS",
    )

    assert lifecycle.status == "EXPIRED_WORTHLESS"
    assert lifecycle.expiry_state == "WORTHLESS"
    assert lifecycle.net_quantity == 1000
    assert lifecycle.unmatched_quantity == 1000
    assert lifecycle.realized_pnl == -500.0


def test_worthless_expiry_with_missing_execution_price_keeps_pnl_unknown():
    row = OptionTransaction(
        transaction_id="1",
        option_ticker="ABCXX125",
        broker="BTG Pactual",
        quantity=-1000,
        average_cost=None,
        total_cost=None,
        as_of=date(2026, 9, 10),
    )
    lifecycle = OptionLifecycleEngine().build(
        (row,),
        contract=OptionContract(
            option_ticker="ABCXX125",
            expiration_date=date(2026, 9, 18),
        ),
        evaluation_date=date(2026, 9, 19),
        expiry_outcome="WORTHLESS",
    )

    assert lifecycle.status == "EXPIRED_WORTHLESS"
    assert lifecycle.realized_pnl is None


def test_exercised_long_option_does_not_invent_option_pnl():
    rows = (tx("1", "ABCXX126", 1000, 0.50, "2026-09-10"),)
    lifecycle = OptionLifecycleEngine().build(
        rows,
        contract=OptionContract(
            option_ticker="ABCXX126",
            expiration_date=date(2026, 9, 18),
            option_type="CALL",
            strike=10.0,
            underlying_ticker="ABC3",
        ),
        evaluation_date=date(2026, 9, 19),
        expiry_outcome="EXERCISED",
    )

    assert lifecycle.status == "EXERCISED"
    assert lifecycle.expiry_state == "EXERCISED"
    assert lifecycle.net_quantity == 1000
    assert lifecycle.realized_pnl == 0.0


def test_assigned_short_option_does_not_invent_option_pnl():
    rows = (tx("1", "ABCXX127", -1000, 0.50, "2026-09-10"),)
    lifecycle = OptionLifecycleEngine().build(
        rows,
        contract=OptionContract(
            option_ticker="ABCXX127",
            expiration_date=date(2026, 9, 18),
            option_type="PUT",
            strike=10.0,
            underlying_ticker="ABC3",
        ),
        evaluation_date=date(2026, 9, 19),
        expiry_outcome="ASSIGNED",
    )

    assert lifecycle.status == "ASSIGNED"
    assert lifecycle.expiry_state == "ASSIGNED"
    assert lifecycle.net_quantity == -1000
    assert lifecycle.realized_pnl == 0.0


def test_exercised_requires_long_option_position():
    rows = (tx("1", "ABCXX128", -1000, 0.50, "2026-09-10"),)

    try:
        OptionLifecycleEngine().build(rows, expiry_outcome="EXERCISED")
    except ValueError as exc:
        assert str(exc) == "EXERCISED requires a net long option position"
    else:
        raise AssertionError("expected ValueError")


def test_assigned_requires_short_option_position():
    rows = (tx("1", "ABCXX129", 1000, 0.50, "2026-09-10"),)

    try:
        OptionLifecycleEngine().build(rows, expiry_outcome="ASSIGNED")
    except ValueError as exc:
        assert str(exc) == "ASSIGNED requires a net short option position"
    else:
        raise AssertionError("expected ValueError")
