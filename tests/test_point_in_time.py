from datetime import datetime, timezone

from b3_agent.schemas.common import DataRecord


def test_point_in_time_availability():
    record = DataRecord(
        instrument_id="B3-PETR4",
        ticker="PETR4",
        observation_timestamp=datetime(
            2026, 2, 28, 0, 0, tzinfo=timezone.utc
        ),
        available_timestamp=datetime(
            2026, 3, 5, 12, 0, tzinfo=timezone.utc
        ),
        source="test",
        ingested_at=datetime(
            2026, 3, 5, 13, 0, tzinfo=timezone.utc
        ),
    )

    decision_before = datetime(
        2026, 3, 5, 11, 59, tzinfo=timezone.utc
    )

    decision_after = datetime(
        2026, 3, 5, 12, 1, tzinfo=timezone.utc
    )

    assert record.is_available_at(decision_before) is False
    assert record.is_available_at(decision_after) is True
