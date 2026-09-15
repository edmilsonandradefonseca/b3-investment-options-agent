from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any


AS_OF = date | datetime
QUALITY_STATUSES = ("VALIDATED", "WARNING", "REJECTED")
ACTIONS = ("BUY", "ACCUMULATE", "SELL_PUT", "SELL_CALL")


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    evidence_type: str
    subject_id: str
    as_of: AS_OF
    value: Any
    source_refs: tuple[str, ...]
    quality_status: str
    provenance: str = ""
    description: str = ""


@dataclass(frozen=True)
class MarketSignal:
    signal_id: str
    signal_type: str
    as_of: AS_OF
    severity: str
    evidence_refs: tuple[str, ...]
    source_refs: tuple[str, ...]
    quality_status: str
    confidence: float | None = None
    description: str = ""


@dataclass(frozen=True)
class MarketThreat:
    threat_id: str
    threat_type: str
    subject_id: str
    as_of: AS_OF
    severity: str
    evidence_refs: tuple[str, ...]
    source_refs: tuple[str, ...]
    quality_status: str
    description: str = ""


@dataclass(frozen=True)
class MarketEvent:
    event_id: str
    event_type: str
    subject_id: str
    event_date: AS_OF
    detected_at: AS_OF
    evidence_refs: tuple[str, ...]
    source_refs: tuple[str, ...]
    quality_status: str
    description: str = ""


@dataclass(frozen=True)
class Opportunity:
    opportunity_id: str
    ticker: str
    instrument_type: str
    action: str
    as_of: AS_OF
    expected_return: float | None = None
    valuation_range_ref: str | None = None
    options_analysis_ref: str | None = None
    quant_features_ref: str | None = None
    capital_requirement: float | None = None
    liquidity_value: float | None = None
    evidence_refs: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    quality_status: str = "VALIDATED"
    rationale: str = ""


@dataclass(frozen=True)
class PortfolioImpact:
    impact_id: str
    subject_id: str
    impact_type: str
    direction: str
    severity: str
    as_of: AS_OF
    affected_position_ids: tuple[str, ...] = ()
    affected_tickers: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    rationale: str = ""


@dataclass(frozen=True)
class RelativeOpportunity:
    relative_opportunity_id: str
    existing_position_id: str
    existing_ticker: str
    candidate_opportunity_id: str
    candidate_ticker: str
    as_of: AS_OF
    comparison_refs: tuple[str, ...] = ()
    portfolio_impact_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    relative_assessment: str = ""
    quality_status: str = "VALIDATED"


@dataclass(frozen=True)
class ActionCandidate:
    action_candidate_id: str
    action_type: str
    subject_id: str
    as_of: AS_OF
    priority: str
    opportunity_refs: tuple[str, ...] = ()
    signal_refs: tuple[str, ...] = ()
    threat_refs: tuple[str, ...] = ()
    event_refs: tuple[str, ...] = ()
    portfolio_impact_refs: tuple[str, ...] = ()
    relative_opportunity_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    rationale: str = ""
    quality_status: str = "VALIDATED"


@dataclass(frozen=True)
class OpportunityAssessment:
    opportunity_id: str
    eligible: bool
    rejection_reasons: tuple[str, ...] = ()
    attractiveness: str = "UNKNOWN"
    portfolio_fit: str = "UNKNOWN"
    portfolio_impact_refs: tuple[str, ...] = ()
    relative_opportunity_refs: tuple[str, ...] = ()
    action_candidate_refs: tuple[str, ...] = ()
    ranking_evidence_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    ranking_key: tuple[object, ...] = ()
    rationale: str = ""
    ticker: str = ""
    instrument_type: str = ""
    action: str = ""
    as_of: AS_OF | None = None
    expected_return: float | None = None
    capital_requirement: float | None = None
    liquidity_value: float | None = None
    valuation_range_ref: str | None = None
    options_analysis_ref: str | None = None
    quant_features_ref: str | None = None
    source_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class OpportunitySet:
    as_of: AS_OF
    ranked_opportunities: tuple[OpportunityAssessment, ...]
    rejected_opportunities: tuple[OpportunityAssessment, ...]
    action_candidates: tuple[ActionCandidate, ...] = ()
    relative_opportunities: tuple[RelativeOpportunity, ...] = ()
    signals: tuple[MarketSignal, ...] = ()
    threats: tuple[MarketThreat, ...] = ()
    events: tuple[MarketEvent, ...] = ()
    impacts: tuple[PortfolioImpact, ...] = ()
    ranking_policy_version: str = ""
    source_refs: tuple[str, ...] = ()
    quality_status: str = "VALIDATED"
