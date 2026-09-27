from pathlib import Path


def test_dashboard_surfaces_deterministic_option_risk_metrics():
    source = Path("mvp/dashboard/app_v06.py").read_text(encoding="utf-8")
    assert '"Uncovered call shares"' in source
    assert "capital_risk.uncovered_call_shares" in source
    assert '"Cash secured"' in source
    assert "capital_risk.fully_cash_secured" in source
    assert '"Call coverage": e.call_coverage_ratio' in source


def test_brokerage_note_validation_message_is_preserved():
    source = Path("mvp/dashboard/app_v06.py").read_text(encoding="utf-8")
    assert "Selecione uma ou mais notas de corretagem em PDF." in source
    assert "if failures:" in source
    assert 'st.session_state.load_error = " | ".join(failures)' in source
