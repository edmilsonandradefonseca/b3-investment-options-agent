from datetime import date

import pytest

from b3_agent.portfolio.lifecycle import PositionLifecycleEngine


def test_position_lifecycle_open_monitor_re_evaluate_close():
    engine = PositionLifecycleEngine()
    current = engine.open("itub4", date(2026, 9, 14))
    current = engine.transition(current, "MONITOR")
    current = engine.transition(current, "RE_EVALUATE", reason="valuation changed")
    current = engine.transition(current, "CLOSE", reason="sell policy")
    assert current.state == "CLOSE"
    assert current.reason == "sell policy"


def test_invalid_lifecycle_transition_is_rejected():
    engine = PositionLifecycleEngine()
    current = engine.open("itub4", date(2026, 9, 14))
    with pytest.raises(ValueError, match="invalid lifecycle transition"):
        engine.transition(current, "ASSIGN")
