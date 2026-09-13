from b3_agent.health_check import health_check


def test_health_check():
    result = health_check()

    assert result["status"] == "ok"
    assert result["service"] == "b3-investment-options-agent"
