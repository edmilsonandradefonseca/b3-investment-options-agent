from __future__ import annotations

from b3_agent.schemas.analysis_run import AnalysisChange, AnalysisChangeSet, AnalysisRun


class AnalysisChangeDetector:
    """Deterministic comparison for the Dashboard 'what changed' surface."""

    def compare(self, previous: AnalysisRun, current: AnalysisRun) -> AnalysisChangeSet:
        if current.as_of < previous.as_of:
            raise ValueError("current analysis must not precede previous analysis")
        if current.request_scope != previous.request_scope:
            raise ValueError("analysis runs must share request_scope")

        changes: list[AnalysisChange] = []
        fields = (
            "feature_snapshot_id",
            "market_regime_id",
            "relevant_learning_ids",
            "opportunity_refs",
            "risk_refs",
            "rationale_ref",
            "quality_status",
        )
        for field in fields:
            before = getattr(previous, field)
            after = getattr(current, field)
            if before != after:
                changes.append(AnalysisChange(field=field, before=before, after=after))

        return AnalysisChangeSet(
            previous_analysis_id=previous.analysis_id,
            current_analysis_id=current.analysis_id,
            changes=tuple(changes),
        )
