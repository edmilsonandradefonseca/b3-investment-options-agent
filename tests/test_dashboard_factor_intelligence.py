from pathlib import Path

def test_dashboard_factor_intelligence_is_statistical_not_causal():
    source=Path("mvp/dashboard/app_v06.py").read_text(encoding="utf-8")
    assert "Factor Intelligence" in source
    assert "Adjusted p" in source
    assert "Walk-forward robustness" in source
    assert "Significância e correlação não demonstram causalidade" in source
