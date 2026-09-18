from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from math import exp, log


class RetentionClass(StrEnum):
    STOCK_MARKET = "stock_market"
    OPTIONS_MARKET = "options_market"
    MARKET_EVIDENCE = "market_evidence"
    MARKET_EVENT = "market_event"
    DECISION = "decision"
    PERSISTENT_KNOWLEDGE = "persistent_knowledge"


class DecayProfile(StrEnum):
    FAST = "fast"
    MEDIUM = "medium"
    SLOW = "slow"
    STRUCTURAL = "structural"
    PERMANENT = "permanent"


@dataclass(frozen=True)
class RetentionPolicy:
    retention_class: RetentionClass
    retention_days: int | None
    decay_profile: DecayProfile
    description: str


@dataclass(frozen=True)
class LifecycleAssessment:
    retention_class: RetentionClass
    first_seen: datetime
    last_updated: datetime
    age_days: float
    retention_days: int | None
    eligible_for_purge: bool
    freshness_score: float
    decay_profile: DecayProfile
    status: str
    purge_at: datetime | None


POLICIES: dict[RetentionClass, RetentionPolicy] = {
    RetentionClass.STOCK_MARKET: RetentionPolicy(
        RetentionClass.STOCK_MARKET, 360, DecayProfile.SLOW,
        "Rolling 360-day window for stock market observations.",
    ),
    RetentionClass.OPTIONS_MARKET: RetentionPolicy(
        RetentionClass.OPTIONS_MARKET, 90, DecayProfile.FAST,
        "Rolling 90-day window for detailed option market observations.",
    ),
    RetentionClass.MARKET_EVIDENCE: RetentionPolicy(
        RetentionClass.MARKET_EVIDENCE, 90, DecayProfile.FAST,
        "Short-lived raw/normalized market evidence; derived events may survive.",
    ),
    RetentionClass.MARKET_EVENT: RetentionPolicy(
        RetentionClass.MARKET_EVENT, None, DecayProfile.MEDIUM,
        "Persistent while the event remains relevant or active.",
    ),
    RetentionClass.DECISION: RetentionPolicy(
        RetentionClass.DECISION, None, DecayProfile.PERMANENT,
        "Permanent audit record for investment decisions.",
    ),
    RetentionClass.PERSISTENT_KNOWLEDGE: RetentionPolicy(
        RetentionClass.PERSISTENT_KNOWLEDGE, None, DecayProfile.PERMANENT,
        "Human-curated persistent knowledge.",
    ),
}

# Half-life controls retrieval priority, not physical deletion.
_HALF_LIFE_DAYS = {
    DecayProfile.FAST: 7.0,
    DecayProfile.MEDIUM: 30.0,
    DecayProfile.SLOW: 90.0,
    DecayProfile.STRUCTURAL: 365.0,
    DecayProfile.PERMANENT: None,
}


class InformationLifecycleEngine:
    """Apply retention, freshness decay and purge eligibility deterministically."""

    def __init__(self, policies: dict[RetentionClass, RetentionPolicy] | None = None):
        self.policies = dict(policies or POLICIES)

    def assess(
        self,
        retention_class: RetentionClass,
        *,
        first_seen: datetime,
        last_updated: datetime | None = None,
        as_of: datetime | None = None,
        status: str = "ACTIVE",
    ) -> LifecycleAssessment:
        now = _aware(as_of or datetime.now(timezone.utc))
        first = _aware(first_seen)
        updated = _aware(last_updated or first)
        if updated < first:
            raise ValueError("last_updated must not precede first_seen")
        if first > now or updated > now:
            raise ValueError("timestamps must not be in the future relative to as_of")

        policy = self.policies[retention_class]
        age_days = max(0.0, (now - updated).total_seconds() / 86400.0)
        purge_at = None if policy.retention_days is None else updated + timedelta(days=policy.retention_days)

        # Active market events are never purged by age alone. They are re-evaluated
        # when new evidence arrives or their status becomes inactive.
        eligible = (
            policy.retention_days is not None
            and now >= purge_at
            and not (retention_class == RetentionClass.MARKET_EVENT and status.upper() == "ACTIVE")
        )
        freshness = _freshness(age_days, policy.decay_profile)

        return LifecycleAssessment(
            retention_class=retention_class,
            first_seen=first,
            last_updated=updated,
            age_days=age_days,
            retention_days=policy.retention_days,
            eligible_for_purge=eligible,
            freshness_score=freshness,
            decay_profile=policy.decay_profile,
            status=status,
            purge_at=purge_at,
        )

    def purge_candidates(
        self,
        records: list[LifecycleAssessment],
    ) -> tuple[LifecycleAssessment, ...]:
        """Return only records that are currently safe to physically purge."""
        return tuple(record for record in records if record.eligible_for_purge)


def _freshness(age_days: float, profile: DecayProfile) -> float:
    half_life = _HALF_LIFE_DAYS[profile]
    if half_life is None:
        return 1.0
    return exp(-log(2.0) * age_days / half_life)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return value
