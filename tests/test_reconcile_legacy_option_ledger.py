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


def _load_module():
    import importlib.util
    path = Path("scripts/reconcile_legacy_option_ledger.py")
    spec = importlib.util.spec_from_file_location("reconcile_legacy_option_ledger", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_canonical_target_uses_runtime_env_file(monkeypatch, tmp_path):
    module = _load_module()
    env1 = tmp_path / "b3-runtime.env"
    env2 = tmp_path / "b3.env"
    env1.write_text("B3_AGENT_DATA_DIR=/tmp/old-runtime\n", encoding="utf-8")
    env2.write_text("B3_AGENT_DATA_DIR=/opt/b3-runtime/data\n", encoding="utf-8")

    monkeypatch.delenv("B3_AGENT_DATA_DIR", raising=False)
    monkeypatch.setattr(module, "RUNTIME_ENV_FILES", (env1, env2))

    assert module._canonical_data_dir() == Path("/opt/b3-runtime/data").resolve()


def test_explicit_process_env_wins_for_canonical_target(monkeypatch, tmp_path):
    module = _load_module()
    env1 = tmp_path / "b3-runtime.env"
    env1.write_text("B3_AGENT_DATA_DIR=/opt/b3-runtime/data\n", encoding="utf-8")

    monkeypatch.setattr(module, "RUNTIME_ENV_FILES", (env1,))
    monkeypatch.setenv("B3_AGENT_DATA_DIR", "/srv/custom-b3-data")

    assert module._canonical_data_dir() == Path("/srv/custom-b3-data").resolve()
