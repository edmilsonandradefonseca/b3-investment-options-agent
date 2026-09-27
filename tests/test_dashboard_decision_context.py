from pathlib import Path

def test_dashboard_surfaces_uc04_uc05_without_inventing_inputs():
    source=Path("mvp/dashboard/app_v06.py").read_text(encoding="utf-8")
    assert "Decision Context" in source
    assert "st.session_state.market_regime" in source
    assert "st.session_state.strategy_comparisons" in source
    assert "st.session_state.stress_results" in source
    assert "right-minus-left" in source
    assert "Choques são inputs explícitos" in source
