from datetime import datetime, timedelta, timezone

import pytest

from b3_agent.knowledge.lifecycle import (
    DecayProfile,
    InformationLifecycleEngine,
    RetentionClass,
)


NOW = datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc)


def test_stock_market_uses_rolling_360_day_window():
    engine = InformationLifecycleEngine()
    assessment = engine.assess(
        RetentionClass.STOCK_MARKET,
        first_seen=NOW - timedelta(days=360),
        last_updated=NOW - timedelta(days=359),
        as_of=NOW,
    )

    assert assessment.retention_days == 360
    assert assessment.eligible_for_purge is False
    assert assessment.purge_at == NOW + timedelta(days=1)


def test_stock_market_record_becomes_purge_candidate_after_360_days():
    engine = InformationLifecycleEngine()
    assessment = engine.assess(
        RetentionClass.STOCK_MARKET,
        first_seen=NOW - timedelta(days=361),
        last_updated=NOW - timedelta(days=361),
        as_of=NOW,
    )

    assert assessment.eligible_for_purge is True


def test_options_and_market_evidence_use_90_day_window():
    engine = InformationLifecycleEngine()
    for retention_class in (
        RetentionClass.OPTIONS_MARKET,
        RetentionClass.MARKET_EVIDENCE,
    ):
        assessment = engine.assess(
            retention_class,
            first_seen=NOW - timedelta(days=91),
            last_updated=NOW - timedelta(days=91),
            as_of=NOW,
        )
        assert assessment.retention_days == 90
        assert assessment.eligible_for_purge is True


def test_active_market_event_is_not_purged_by_age():
    engine = InformationLifecycleEngine()
    assessment = engine.assess(
        RetentionClass.MARKET_EVENT,
        first_seen=NOW - timedelta(days=400),
        last_updated=NOW - timedelta(days=400),
        as_of=NOW,
        status="ACTIVE",
    )

    assert assessment.retention_days is None
    assert assessment.eligible_for_purge is False
    assert assessment.freshness_score < 1.0


def test_permanent_records_have_no_freshness_decay():
    engine = InformationLifecycleEngine()
    assessment = engine.assess(
        RetentionClass.DECISION,
        first_seen=NOW - timedelta(days=5000),
        last_updated=NOW - timedelta(days=5000),
        as_of=NOW,
    )

    assert assessment.decay_profile == DecayProfile.PERMANENT
    assert assessment.retention_days is None
    assert assessment.freshness_score == 1.0
    assert assessment.eligible_for_purge is False


def test_freshness_decays_monotonically():
    engine = InformationLifecycleEngine()
    recent = engine.assess(
        RetentionClass.MARKET_EVIDENCE,
        first_seen=NOW - timedelta(days=5),
        last_updated=NOW - timedelta(days=5),
        as_of=NOW,
    )
    old = engine.assess(
        RetentionClass.MARKET_EVIDENCE,
        first_seen=NOW - timedelta(days=30),
        last_updated=NOW - timedelta(days=30),
        as_of=NOW,
    )

    assert 0.0 < old.freshness_score < recent.freshness_score < 1.0


def test_naive_timestamps_are_rejected():
    engine = InformationLifecycleEngine()
    naive = datetime(2026, 9, 17, 12, 0)

    with pytest.raises(ValueError, match="timezone-aware"):
        engine.assess(
            RetentionClass.STOCK_MARKET,
            first_seen=naive,
            as_of=NOW,
        )
