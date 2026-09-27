from pathlib import Path


def test_dashboard_v4_e2e_has_no_obsidian_runtime_reference():
    source = Path("mvp/dashboard/app_v06.py").read_text(encoding="utf-8")
    assert "Obsidian" not in source
    assert "SQLite / Parquet" in source
    assert "Qdrant projection" in source
    assert "Neo4j projection" in source


def test_dashboard_does_not_fabricate_opportunities_from_portfolio():
    source = Path("mvp/dashboard/app_v06.py").read_text(encoding="utf-8")
    assert "DashboardE2EService().load(" in source
    assert "opportunity_set = st.session_state.opportunities" in source
    assert "não converte exposição de portfolio em oportunidade" in source
