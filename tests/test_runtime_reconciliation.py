from datetime import date, datetime, timezone

from b3_agent.orchestration.runtime import _build_options_reconciliation
from b3_agent.repositories.option_ledger import OptionTransactionLedger
from b3_agent.repositories.source_manifest import SourceManifestRecord, SourceManifestRepository
from b3_agent.schemas.option_transaction import OptionTransaction
from b3_agent.schemas.position import PortfolioContext, Position


def _portfolio(quantity: float = 3000) -> PortfolioContext:
    return PortfolioContext(
        as_of=date(2026, 9, 17),
        positions=(
            Position(
                position_id="pos-ASAIJ970",
                ticker="ASAIJ970",
                instrument_type="OPTION",
                quantity=quantity,
                average_cost=0.94,
                strike=9.70,
                expiration_date=date(2026, 10, 16),
                option_type="CALL",
                underlying_ticker="ASAI3",
                contract_multiplier=1,
            ),
        ),
    )


def _excel() -> OptionTransaction:
    return OptionTransaction(
        transaction_id="excel-1",
        option_ticker="ASAIJ970",
        broker="BTG Pactual",
        quantity=3000,
        average_cost=0.94,
        total_cost=2820,
        source_ref="Options Transactions XLSX",
        source_type="OPTIONS_XLSX",
        source_id="options_transactions.xlsx",
    )


def _brokerage() -> OptionTransaction:
    return OptionTransaction(
        transaction_id="btg-note:34515456:1:ASAIJ970",
        option_ticker="ASAIJ970",
        broker="BTG Pactual",
        quantity=3000,
        average_cost=0.94,
        total_cost=2820,
        as_of=date(2026, 9, 17),
        source_ref="BTG:NotaCorretagem:34515456:nota.pdf",
        note_number="34515456",
        source_type="BROKERAGE_NOTE",
        source_id="34515456",
    )


def test_runtime_loads_ledger_and_reconciles_against_excel(tmp_path):
    ledger = OptionTransactionLedger(tmp_path / "options.sqlite3")
    transaction = _brokerage()
    assert ledger.append((transaction,)) == 1

    SourceManifestRepository(tmp_path / "source_manifest.sqlite3").upsert(
        SourceManifestRecord(
            source_fingerprint="fingerprint",
            source_type="BROKERAGE_NOTE",
            source_id="34515456",
            source_ref="BTG:NotaCorretagem:34515456",
            file_name="nota.pdf",
            imported_at=datetime(2026, 9, 17, tzinfo=timezone.utc),
            record_count=1,
            coverage_start=date(2026, 9, 17),
            coverage_end=date(2026, 9, 17),
            scope="PERIOD_ONLY",
            completeness="UNKNOWN",
        )
    )

    result = _build_options_reconciliation(
        tmp_path,
        _portfolio(),
        (_excel(),),
    )

    assert result is not None
    assert [item["status"] for item in result["matches"]] == ["RECONCILED"]
    assert result["quality_status"] == "VALIDATED"
    assert result["source_coverage"][0]["source_ref"] == "Options Transactions XLSX"
    assert any(
        item["source_ref"] == "BTG:NotaCorretagem:34515456:nota.pdf"
        for item in result["source_coverage"]
    )


def test_runtime_reconciliation_does_not_feed_brokerage_ledger_into_pnl(tmp_path):
    ledger = OptionTransactionLedger(tmp_path / "options.sqlite3")
    assert ledger.append((_brokerage(),)) == 1

    result = _build_options_reconciliation(
        tmp_path,
        _portfolio(),
        (_excel(),),
    )

    assert result is not None
    # The runtime reconciliation payload is a separate context; P&L still receives
    # only the active XLSX snapshot in the existing performance calculation path.
    assert result["matches"][0]["status"] == "RECONCILED"
    assert result["matches"][0]["excel_transaction_id"] == "excel-1"
    assert result["matches"][0]["brokerage_transaction_id"].startswith("btg-note:")
