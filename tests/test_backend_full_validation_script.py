from pathlib import Path


def test_backend_full_validation_script_covers_all_production_gates():
    path = Path("scripts/backend_full_validation.sh")
    source = path.read_text(encoding="utf-8")

    for marker in (
        "FULL PYTEST REGRESSION",
        "REAL SHARED BACKEND ACCEPTANCE",
        "REAL UC01..UC12 ACCEPTANCE",
        "FAST ROUTER HTTP E2E",
        "SERVICES AND TIMERS",
        "DEEPSEEK LOCAL RUNTIME",
        "OPENCLAW/LUNA TRANSPORT",
        "B3 RUNTIME ERROR SCAN",
        "B3 BACKEND FULL VALIDATION: PASS",
    ):
        assert marker in source

    for uc in ("UC-01", "UC-02", "UC-11"):
        assert uc in source

    assert "joao-scheduler.service" in source
    assert "systemctl stop" not in source
    assert "systemctl start" not in source
    assert "systemctl restart" not in source


def test_backend_full_validation_keeps_paid_api_errors_visible():
    source = Path("scripts/backend_full_validation.sh").read_text(encoding="utf-8")
    assert "insufficient_quota" in source
    assert "credit_balance_exhausted" in source
    assert "429" in source


def test_backend_full_validation_runs_defaults_before_loading_production_env():
    source = Path("scripts/backend_full_validation.sh").read_text(encoding="utf-8")
    gate1 = source.index('run_gate "GATE 1 - FULL PYTEST REGRESSION"')
    load_env = source.index("\nload_env\n", gate1)
    gate2 = source.index('run_gate "GATE 2 - REAL SHARED BACKEND ACCEPTANCE"')
    assert gate1 < load_env < gate2
    assert "pytest_clean_gate" in source


def test_backend_full_validation_surfaces_limited_use_cases():
    source = Path("scripts/backend_full_validation.sh").read_text(encoding="utf-8")
    assert 'run_gate "GATE 3 - REAL UC01..UC12 ACCEPTANCE"' in source
    assert "uc_acceptance_gate" in source
    assert "LIMITED use case(s)" in source
