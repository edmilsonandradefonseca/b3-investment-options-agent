from __future__ import annotations

from b3_agent.schemas.decision import DecisionProposal, RiskValidation


class RiskValidator:
    """Deterministic safety gate for the MVP decision proposal."""

    def validate(self, decision: DecisionProposal) -> RiskValidation:
        reasons: list[str] = []

        if not decision.subject_id.strip():
            reasons.append("missing_subject_id")
        if not decision.thesis.strip():
            reasons.append("missing_thesis")
        if not decision.rationale.strip():
            reasons.append("missing_rationale")
        if not decision.evidence_refs:
            reasons.append("missing_evidence_refs")
        if decision.action.strip().upper() in {"EXECUTE", "PLACE_ORDER", "TRADE"}:
            reasons.append("execution_not_allowed_in_mvp")

        return RiskValidation(
            status="REJECT" if reasons else "PASS",
            reasons=tuple(reasons),
        )
