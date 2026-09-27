from pathlib import Path


def test_streamlit_uses_dashboard_e2e_service_for_uploaded_snapshot():
    source = Path("mvp/dashboard/app_v06.py").read_text(encoding="utf-8")
    assert "DashboardE2EService().load(" in source
    assert "snapshot.portfolio" in source
    assert "snapshot.portfolio_intelligence" in source
    assert "snapshot.option_transactions" in source
    assert "snapshot.opportunities" in source


def test_options_upload_requires_portfolio_snapshot():
    source = Path("mvp/dashboard/app_v06.py").read_text(encoding="utf-8")
    assert "Carregue o BTG Portfolio junto com Options Transactions" in source
