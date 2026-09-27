from pathlib import Path


def test_real_uc_acceptance_script_has_all_use_cases():
    text = Path("scripts/uc_real_acceptance.py").read_text(encoding="utf-8")
    for number in range(1, 13):
        assert f'"UC-{number:02d}"' in text
    assert '"LIMITED"' in text
    assert "B3 REAL UC01-UC12 ACCEPTANCE" in text
    assert "B3 REAL UC ACCEPTANCE COMPLETED" in text


def test_real_uc_acceptance_compiles():
    source = Path("scripts/uc_real_acceptance.py").read_text(encoding="utf-8")
    compile(source, "scripts/uc_real_acceptance.py", "exec")


def test_acceptance_prefers_configurable_representative_ticker():
    text = Path("scripts/uc_real_acceptance.py").read_text(encoding="utf-8")
    assert 'os.getenv("B3_ACCEPTANCE_TICKER", "PETR4")' in text
    assert 'if "PETR4" in portfolio_tickers' in text


def test_real_uc_acceptance_uses_live_source_refs():
    text = Path("scripts/uc_real_acceptance.py").read_text(encoding="utf-8")
    assert "source_refs=live.source_refs" in text
    assert "source_refs=live.sources" not in text


def test_real_uc_acceptance_has_multiticker_brapi_smoke():
    text = Path("scripts/uc_real_acceptance.py").read_text(encoding="utf-8")
    assert "B3_ACCEPTANCE_TICKERS" in text
    assert "BRAPI MULTI-TICKER OK" in text
    assert "_validate_brapi_market" in text


def test_real_uc_acceptance_loads_shared_env():
    text = Path("scripts/uc_real_acceptance.py").read_text(encoding="utf-8")
    assert "_load_shared_env()" in text
    assert "/opt/joao-runtime/joao.env" in text
