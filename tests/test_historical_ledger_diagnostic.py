from pathlib import Path


def test_historical_ledger_diagnostic_is_read_only_and_targets_canonical_path():
    path = Path("scripts/historical_ledger_diagnostic.py")
    source = path.read_text(encoding="utf-8")
    compile(source, str(path), "exec")

    assert 'canonical = canonical_data_dir / "options.sqlite3"' in source
    assert 'canonical_manifest = canonical_data_dir / "source_manifest.sqlite3"' in source
    assert 'Path("/etc/b3-runtime.env")' in source
    assert 'Path("/opt/b3-runtime/b3.env")' in source
    assert 'Path("/opt/b3-runtime/data")' in source
    assert "canonical_uc07_usable_rows" in source
    assert "CANONICAL_LEDGER_READY" in source
    assert "LEDGER_EXISTS_OUTSIDE_CANONICAL_DATA_DIR" in source
    assert "CANONICAL_PDFS_PRESENT_LEDGER_MISSING" in source

    # Diagnostic must not ingest, copy, move or delete user data.
    for forbidden in (
        "OptionTransactionLedger(canonical).append(",
        "OptionTransactionLedger(ledger).append(",
        ".write_bytes(",
        ".write_text(",
        ".unlink(",
        ".replace(",
        "shutil.copy",
        "shutil.move",
    ):
        assert forbidden not in source


def test_historical_ledger_diagnostic_resolves_runtime_env_before_repo_data():
    source = Path("scripts/historical_ledger_diagnostic.py").read_text(encoding="utf-8")
    assert "def _canonical_data_dir()" in source
    assert 'os.getenv("B3_AGENT_DATA_DIR")' in source
    assert "RUNTIME_ENV_FILES" in source
    assert "DEFAULT_RUNTIME_DATA.resolve()" in source
