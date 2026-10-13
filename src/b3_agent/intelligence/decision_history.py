"""Candidate-bound observations, not an Experience/Learning truth store."""
from dataclasses import asdict, dataclass
from typing import Any

from b3_agent.intelligence.personal_history import PersonalHistoryService

MAX_CANDIDATES = 20


@dataclass(frozen=True)
class HistoryTarget:
    candidate_id: str
    subject_id: str
    action: str


def _items(value):
    return value if isinstance(value, (list, tuple)) else ()


def _targets(result: dict[str, Any], tickers: tuple[str, ...]) -> list[HistoryTarget]:
    targets = []
    comparison = result.get("strategy_comparison") or {}
    opportunity_set = result.get("opportunity_set") or {}
    if isinstance(comparison, dict):
        for item in _items(comparison.get("alternatives")):
            if isinstance(item, dict) and item.get("subject_id") and item.get("alternative_id"):
                subject = str(item["subject_id"]).strip().upper()
                if subject:
                    targets.append(HistoryTarget(str(item["alternative_id"]), subject, str(item.get("action_type") or "ANALYZE")))
    if isinstance(opportunity_set, dict):
        for item in _items(opportunity_set.get("ranked_opportunities")):
            if isinstance(item, dict) and item.get("opportunity_id"):
                if (item.get("instrument_type") == "OPTION" or item.get("action") in {"SELL_PUT", "SELL_CALL"}) and not item.get("options_analysis_ref"):
                    # An underlying ticker is not an option contract identity.
                    continue
                subject = item.get("options_analysis_ref") or item.get("ticker")
                if subject and str(subject).strip():
                    targets.append(HistoryTarget(str(item["opportunity_id"]), str(subject).strip().upper(), str(item.get("action") or "ANALYZE")))
    if not targets:
        targets = [HistoryTarget(f"ASSET:{ticker}", ticker.strip().upper(), "ANALYZE") for ticker in tickers if ticker.strip()]
    # Preserve candidate order; two distinct strategies can share one subject.
    return list(dict.fromkeys(targets))


def build_decision_history(
    service: PersonalHistoryService, *, result: dict[str, Any],
    tickers: tuple[str, ...] = (), as_of=None, since=None,
) -> dict[str, Any]:
    targets = _targets(result, tickers)
    projections = {}
    candidates = []
    for target in targets[:MAX_CANDIDATES]:
        if target.subject_id not in projections:
            projections[target.subject_id] = service.build(
                ticker=target.subject_id, exact_symbol=True, as_of=as_of, since=since,
            )
        candidates.append({**asdict(target), "history_subject": target.subject_id})
    return {
        "policy_version": "decision-history-v1",
        "authority": "existing_sqlite_execution_projection",
        "match_policy": "EXACT_SYMBOL",
        "candidates": candidates,
        "subjects": projections,
        "candidate_details_omitted": max(0, len(targets)-MAX_CANDIDATES),
        "ranking_effect": "NONE",
        "canonical_experience_status": "NOT_ADMITTED_BY_EXECUTION_PROJECTION",
        "limitations": [
            "Exact-symbol executions are observations, not validated comparable strategies.",
            "Candidate actions and current option metadata do not classify historical strategy or prove entry features.",
            "Unknown outcomes cannot support a success rate, assignment probability or historical winner.",
            "Absent supporting/contradicting learnings means unavailable canonical evidence, not confirmation of a thesis.",
        ],
    }
