from pathlib import Path


def test_historical_ledger_diagnostic_is_read_only_and_targets_canonical_path():
    path = Path("scripts/historical_ledger_diagnostic.py")
    source = path.read_text(encoding="utf-8")
    compile(source, str(path), "exec")

    assert 'settings.data_dir / "options.sqlite3"' in source
    assert 'settings.data_dir / "source_manifest.sqlite3"' in source
    assert "canonical_uc07_usable_rows" in source
    assert "CANONICAL_LEDGER_READY" in source
    assert "LEDGER_EXISTS_OUTSIDE_CANONICAL_DATA_DIR" in source
    assert "CANONICAL_PDFS_PRESENT_LEDGER_MISSING" in source

    # Diagnostic must not ingest, copy, move or delete user data.
    for forbidden in (
        ".append(",
        ".write_bytes(",
        ".write_text(",
        ".unlink(",
        ".replace(",
        "shutil.copy",
        "shutil.move",
    ):
        assert forbidden not in source
