from pathlib import Path


def test_dashboard_renders_domain_expiration_risk_and_concentration():
    source = Path("mvp/dashboard/app_v06.py").read_text(encoding="utf-8")
    assert "intelligence.expiration_risk" in source
    assert '"Risk by expiration"' in source
    assert '"Top 5 concentration"' in source
    assert 'sort_values("Peso", ascending=False).head(5)' in source
