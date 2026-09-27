from pathlib import Path


def test_opportunities_tab_renders_traceable_ranked_inputs_when_available():
    source = Path("mvp/dashboard/app_v06.py").read_text(encoding="utf-8")
    assert "opportunity_set.ranked_opportunities" in source
    assert '"Retorno esperado"' in source
    assert '"Capital requerido"' in source
    assert '"Valuation ref"' in source
    assert '"Options ref"' in source
    assert '"Quant ref"' in source
    assert '"Fontes"' in source
    assert "ranking_policy_version" in source
