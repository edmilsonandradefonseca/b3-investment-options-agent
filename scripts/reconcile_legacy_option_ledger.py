#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from b3_agent.config import settings
from b3_agent.repositories.option_ledger import OptionTransactionLedger


DEFAULT_LEGACY = Path("/opt/b3-investment-options-agent/data/options.sqlite3")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reconcile legacy BTG option-ledger rows into the canonical runtime ledger."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_LEGACY,
        help="legacy options.sqlite3 path",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="append validated rows to the canonical ledger; default is dry-run",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    source = args.source.expanduser().resolve()
    target = (settings.data_dir / "options.sqlite3").resolve()

    print("===== B3 LEGACY OPTION LEDGER RECONCILIATION =====")
    print(f"mode={'APPLY' if args.apply else 'DRY_RUN'}")
    print(f"source={source}")
    print(f"target={target}")

    if source == target:
        print("RESULT=NOOP_SOURCE_IS_CANONICAL")
        return 0
    if not source.is_file():
        print("RESULT=SOURCE_LEDGER_NOT_FOUND")
        return 2

    rows = OptionTransactionLedger(source).list_all()
    if not rows:
        print("RESULT=SOURCE_LEDGER_EMPTY")
        return 3

    invalid = [
        row
        for row in rows
        if row.source_type.upper().strip() != "BROKERAGE_NOTE"
        or row.as_of is None
        or row.execution_price is None
    ]

    print(f"source_rows={len(rows)}")
    print(f"validated_rows={len(rows) - len(invalid)}")
    print(f"invalid_rows={len(invalid)}")

    for row in rows:
        print(
            "ROW "
            f"id={row.transaction_id} "
            f"ticker={row.option_ticker} "
            f"side={row.side} "
            f"qty={row.absolute_quantity:g} "
            f"price={row.execution_price} "
            f"date={row.as_of} "
            f"broker={row.broker!r} "
            f"note_number={row.note_number!r} "
            f"source_type={row.source_type!r} "
            f"source_id={row.source_id!r} "
            f"source_ref={row.source_ref!r}"
        )

    if invalid:
        print("RESULT=REFUSED_INVALID_OR_NON_BROKERAGE_ROWS")
        return 4

    if not args.apply:
        print("RESULT=DRY_RUN_VALID")
        print("No data was written. Re-run with --apply after provenance review.")
        return 0

    target.parent.mkdir(parents=True, exist_ok=True)
    ledger = OptionTransactionLedger(target)
    before = len(ledger.list_all())
    inserted = ledger.append(rows)
    after_rows = ledger.list_all()
    after = len(after_rows)

    source_fingerprints = {OptionTransactionLedger.fingerprint(row) for row in rows}
    target_fingerprints = {
        OptionTransactionLedger.fingerprint(row) for row in after_rows
    }
    missing = source_fingerprints - target_fingerprints

    print(f"canonical_before={before}")
    print(f"inserted={inserted}")
    print(f"canonical_after={after}")
    print(f"missing_after_verify={len(missing)}")

    if missing:
        print("RESULT=VERIFY_FAILED")
        return 5

    print("RESULT=APPLIED_AND_VERIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
