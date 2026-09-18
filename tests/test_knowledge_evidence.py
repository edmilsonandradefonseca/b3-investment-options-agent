from datetime import datetime, timezone

import pytest

from b3_agent.knowledge.evidence import Evidence, EvidenceKind, EvidenceMetadata
from b3_agent.knowledge.lifecycle import DecayProfile, RetentionClass


UTC = timezone.utc


def metadata(**overrides):
    values = {
        "document_id": "news-001",
        "source": "Reuters:news-001",
        "published_at": datetime(2026, 9, 17, 9, 0, tzinfo=UTC),
        "retrieved_at": datetime(2026, 9, 17, 9, 5, tzinfo=UTC),
        "ticker_refs": ("petr4", "PETR4", " vale3 "),
        "sector_refs": ("energy",),
        "event_refs": ("event-1", "event-1"),
        "topic": "oil",
        "source_quality": "primary",
        "confidence": 0.9,
        "retention_class": RetentionClass.MARKET_EVIDENCE,
        "decay_profile": DecayProfile.FAST,
    }
    values.update(overrides)
    return EvidenceMetadata(**values)


def test_metadata_normalizes_references_and_preserves_contract():
    item = metadata()
    assert item.ticker_refs == ("PETR4", "VALE3")
    assert item.sector_refs == ("ENERGY",)
    assert item.event_refs == ("event-1",)


def test_point_in_time_excludes_future_evidence():
    item = metadata()
    as_of = datetime(2026, 9, 17, 9, 2, tzinfo=UTC)
    assert item.is_available_at(as_of) is False


def test_point_in_time_accepts_available_evidence():
    item = metadata()
    as_of = datetime(2026, 9, 17, 9, 6, tzinfo=UTC)
    assert item.is_available_at(as_of) is True


def test_validity_window_is_enforced():
    item = metadata(
        valid_from=datetime(2026, 9, 17, 10, 0, tzinfo=UTC),
        valid_to=datetime(2026, 9, 18, 10, 0, tzinfo=UTC),
    )
    assert item.is_available_at(datetime(2026, 9, 17, 9, 0, tzinfo=UTC)) is False
    assert item.is_available_at(datetime(2026, 9, 17, 12, 0, tzinfo=UTC)) is True


def test_evidence_requires_http_source_url():
    item = Evidence(
        evidence_id="e-1",
        kind=EvidenceKind.NEWS,
        title="Market event",
        content="Relevant market evidence.",
        metadata=metadata(),
        source_url="https://example.com/news/e-1",
    )
    assert item.source_ref == "Reuters:news-001"

    with pytest.raises(ValueError):
        Evidence(
            evidence_id="e-2",
            kind=EvidenceKind.NEWS,
            title="Market event",
            content="Relevant market evidence.",
            metadata=metadata(),
            source_url="not-a-url",
        )


def test_confidence_must_be_bounded():
    with pytest.raises(ValueError):
        metadata(confidence=1.1)


def test_timestamps_must_be_timezone_aware():
    with pytest.raises(ValueError):
        metadata(retrieved_at=datetime(2026, 9, 17, 9, 5))
