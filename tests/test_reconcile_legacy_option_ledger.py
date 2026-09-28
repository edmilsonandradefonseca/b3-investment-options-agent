from pathlib import Path


def test_legacy_ledger_reconciliation_is_dry_run_by_default():
    source = Path("scripts/reconcile_legacy_option_ledger.py").read_text(encoding="utf-8")
    compile(source, "scripts/reconcile_legacy_option_ledger.py", "exec")

    assert 'action="store_true"' in source
    assert "RESULT=DRY_RUN_VALID" in source
    assert "Re-run with --apply" in source
    assert "BROKERAGE_NOTE" in source
    assert "missing_after_verify" in source
    assert "RESULT=APPLIED_AND_VERIFIED" in source


def test_legacy_ledger_reconciliation_preserves_append_only_semantics():
    source = Path("scripts/reconcile_legacy_option_ledger.py").read_text(encoding="utf-8")
    assert "ledger.append(rows)" in source
    for forbidden in (
        ".unlink(",
        ".replace(",
        "shutil.move",
        "shutil.copy",
        "DELETE FROM",
        "UPDATE option_transactions",
    ):
        assert forbidden not in source
