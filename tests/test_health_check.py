from b3_agent.health_check import health_check


def test_health_check():
    result = health_check()

    assert result["status"] == "ok"
    assert result["service"] == "b3-investment-options-agent"
    assert result["environment"] == "development"
    assert result["timezone"] == "America/Sao_Paulo"
    assert result["llm_enabled"] is False


def test_health_check_includes_required_checks():
    result = health_check()

    checks = result["checks"]

    assert checks["project_root_exists"] is True
    assert checks["data_dir_available"] is True
    assert checks["logs_dir_available"] is True
