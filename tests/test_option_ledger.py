from datetime import date

from b3_agent.repositories.option_ledger import OptionTransactionLedger
from b3_agent.schemas.option_transaction import OptionTransaction


def make_tx(transaction_id: str) -> OptionTransaction:
    return OptionTransaction(
        transaction_id=transaction_id,
        option_ticker="EQTLV369",
        broker="BTG Pactual",
        quantity=-1000,
        average_cost=0.64,
        total_cost=-640.0,
        as_of=date(2026, 9, 11),
        note_number="34405429",
    )


def test_fingerprint_is_independent_of_transaction_id():
    assert OptionTransactionLedger.fingerprint(make_tx("A")) == OptionTransactionLedger.fingerprint(make_tx("B"))


def test_ledger_deduplicates_same_economic_transaction(tmp_path):
    ledger = OptionTransactionLedger(tmp_path / "ledger.sqlite3")
    assert ledger.append((make_tx("A"),)) == 1
    assert ledger.append((make_tx("B"),)) == 0
    assert len(ledger.list_all()) == 1
