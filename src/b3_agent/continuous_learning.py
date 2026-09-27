from __future__ import annotations
from dataclasses import dataclass
from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime
from b3_agent.experience.model import Experience
from b3_agent.learning import LearningEngine, LearningUpdateResult

@dataclass(frozen=True)
class ContinuousLearningSnapshot:
    updates: tuple[LearningUpdateResult, ...]
    experience_count: int

class ContinuousLearningService:
    """UC-08 deterministic learning over compatible personal-experience cohorts."""
    def build(self, experiences: Iterable[Experience], *, as_of: datetime) -> ContinuousLearningSnapshot:
        rows=tuple(experiences)
        cohorts=defaultdict(list)
        for exp in rows:
            signature=tuple((d.name.value,d.label) for d in exp.market_regime.dimensions)
            cohorts[(exp.operation.underlying_id,exp.operation.strategy_type,signature)].append(exp)
        engine=LearningEngine()
        updates=tuple(engine.learn(cohort,as_of=as_of) for _,cohort in sorted(cohorts.items(),key=lambda x:str(x[0])))
        return ContinuousLearningSnapshot(updates=updates,experience_count=len(rows))
