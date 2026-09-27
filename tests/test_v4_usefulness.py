from datetime import datetime, timezone

import pytest

from b3_agent.repositories.usefulness import UsefulnessAttributionRepository
from b3_agent.schemas.usefulness import (
    DecisionEvidenceOutcomeAttribution,
    OutcomeAssociation,
)
from b3_agent.storage.sqlite import SQLiteStore
from b3_agent.usefulness import HistoricalUsefulnessEngine, HistoricalUsefulnessPolicy


NOW = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)


def observation(identifier, association, confidence=1.0, evidence_ref="LRN-1"):
    return DecisionEvidenceOutcomeAttribution(
        attribution_id=identifier,
        decision_id=f"DEC-{identifier}",
        evidence_ref=evidence_ref,
        outcome_id=f"OUT-{identifier}",
        observed_at=NOW,
        association=association,
        attribution_confidence=confidence,
        rationale="Explicit association observation; not a causal claim.",
        source_refs=(f"SRC-{identifier}",),
    )


def test_usefulness_uses_neutral_prior_and_low_sample_shrinkage():
    engine = HistoricalUsefulnessEngine(
        HistoricalUsefulnessPolicy(prior_score=0.5, prior_weight=4.0)
    )
    result = engine.assess(
        "LRN-1",
        (observation("1", OutcomeAssociation.POSITIVE),),
    )
    assert result.usefulness_score == pytest.approx(0.6)
    assert result.observation_count == 1
    assert result.positive_weight == pytest.approx(1.0)


def test_inconclusive_does_not_become_positive_confirmation():
    engine = HistoricalUsefulnessEngine()
    result = engine.assess(
        "LRN-1",
        (observation("1", OutcomeAssociation.INCONCLUSIVE),),
    )
    assert result.usefulness_score == pytest.approx(0.5)
    assert result.inconclusive_weight == pytest.approx(1.0)


def test_profitable_outcome_cannot_automatically_confirm_evidence():
    # The engine receives explicit association observations, not P&L/return.
    # A later profitable Outcome therefore has no implicit path to POSITIVE.
    engine = HistoricalUsefulnessEngine()
    result = engine.assess("LRN-1", ())
    assert result.usefulness_score == pytest.approx(0.5)
    assert result.observation_count == 0


def test_repository_roundtrip_and_scores(tmp_path):
    store = SQLiteStore(tmp_path / "b3.db")
    store.initialize()
    repo = UsefulnessAttributionRepository(store)
    repo.save(observation("1", OutcomeAssociation.POSITIVE, 0.8))
    repo.save(observation("2", OutcomeAssociation.NEGATIVE, 0.4))

    loaded = repo.list_for_evidence("LRN-1")
    assert len(loaded) == 2
    assert loaded[0].source_refs == ("SRC-1",)

    scores = repo.scores(HistoricalUsefulnessEngine())
    assert scores["LRN-1"] == pytest.approx((2.0 + 0.8) / (4.0 + 1.2))
