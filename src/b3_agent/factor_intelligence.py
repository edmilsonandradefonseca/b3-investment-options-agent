from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from datetime import date, datetime

from b3_agent.schemas.factor import FactorObservation, FactorStudy, FactorTestResult, FactorWalkForwardFold, FactorWalkForwardResult

AS_OF = date | datetime


class FactorIntelligenceEngine:
    """Conservative factor validation. Association is never labeled causation."""

    def analyze(
        self,
        factors: Mapping[str, Sequence[FactorObservation]],
        *,
        as_of: AS_OF,
        alpha: float = 0.05,
        holdout_fraction: float = 0.30,
        min_sample_size: int = 30,
        source_refs: tuple[str, ...] = (),
    ) -> FactorStudy:
        if not 0 < alpha < 1:
            raise ValueError("alpha must be between 0 and 1")
        if not 0 < holdout_fraction < 1:
            raise ValueError("holdout_fraction must be between 0 and 1")
        if min_sample_size < 4:
            raise ValueError("min_sample_size must be at least 4")

        raw = []
        for factor_id, observations in sorted(factors.items()):
            ordered = sorted(observations, key=lambda item: item.observed_at)
            n = len(ordered)
            if n < min_sample_size:
                raw.append((factor_id, n, 0, 0, None, None, None, None, False, "WARNING"))
                continue
            split = max(2, min(n - 2, int(n * (1.0 - holdout_fraction))))
            train, holdout = ordered[:split], ordered[split:]
            train_r = _correlation(train)
            holdout_r = _correlation(holdout)
            t_stat, p_value = _correlation_test(train_r, len(train))
            stable = train_r is not None and holdout_r is not None and train_r * holdout_r > 0
            raw.append((factor_id, n, len(train), len(holdout), train_r, holdout_r, t_stat, p_value, stable, "VALIDATED"))

        adjusted = _benjamini_hochberg({item[0]: item[7] for item in raw if item[7] is not None})
        results = tuple(
            FactorTestResult(
                factor_id=item[0], sample_size=item[1], train_size=item[2], holdout_size=item[3],
                train_correlation=item[4], holdout_correlation=item[5], t_statistic=item[6], p_value=item[7],
                adjusted_p_value=adjusted.get(item[0]),
                statistically_significant=(adjusted.get(item[0], 1.0) <= alpha and item[8]),
                direction_stable=item[8], quality_status=item[9], as_of=as_of, source_refs=source_refs,
            )
            for item in raw
        )
        return FactorStudy(as_of=as_of, results=results, alpha=alpha, holdout_fraction=holdout_fraction, min_sample_size=min_sample_size)

    def walk_forward(
        self,
        factor_id: str,
        observations: Sequence[FactorObservation],
        *,
        as_of: AS_OF,
        train_size: int = 30,
        test_size: int = 10,
    ) -> FactorWalkForwardResult:
        ordered = sorted(observations, key=lambda item: item.observed_at)
        if train_size < 3 or test_size < 2:
            raise ValueError("train_size >= 3 and test_size >= 2 are required")
        folds = []
        cursor = train_size
        while cursor + test_size <= len(ordered):
            train = ordered[cursor-train_size:cursor]
            test = ordered[cursor:cursor+test_size]
            train_r = _correlation(train); test_r = _correlation(test)
            stable = train_r is not None and test_r is not None and train_r * test_r > 0
            folds.append(FactorWalkForwardFold(train[0].observed_at, train[-1].observed_at, test[0].observed_at, test[-1].observed_at, train_r, test_r, stable))
            cursor += test_size
        test_values = sorted(f.test_correlation for f in folds if f.test_correlation is not None)
        median = None
        if test_values:
            mid=len(test_values)//2
            median=test_values[mid] if len(test_values)%2 else (test_values[mid-1]+test_values[mid])/2
        stable_ratio=sum(f.direction_stable for f in folds)/len(folds) if folds else 0.0
        return FactorWalkForwardResult(factor_id, as_of, tuple(folds), stable_ratio, median, "VALIDATED" if folds else "WARNING")


def _correlation(observations: Sequence[FactorObservation]) -> float | None:
    if len(observations) < 2:
        return None
    xs=[x.factor_value for x in observations]; ys=[x.forward_return for x in observations]
    mx=sum(xs)/len(xs); my=sum(ys)/len(ys)
    numerator=sum((x-mx)*(y-my) for x,y in zip(xs,ys))
    denominator=math.sqrt(sum((x-mx)**2 for x in xs)*sum((y-my)**2 for y in ys))
    return numerator/denominator if denominator else None


def _correlation_test(r: float | None, n: int) -> tuple[float | None, float | None]:
    if r is None or n < 3:
        return None, None
    if abs(r) >= 1.0:
        return math.copysign(math.inf, r), 0.0
    t=r*math.sqrt((n-2)/(1-r*r))
    # Normal approximation is deliberately dependency-free; conservative enough for V1 screening.
    p=math.erfc(abs(t)/math.sqrt(2.0))
    return t, p


def _benjamini_hochberg(values: Mapping[str, float]) -> dict[str, float]:
    ranked=sorted(values.items(), key=lambda item:item[1]); m=len(ranked); out={}; running=1.0
    for rank in range(m,0,-1):
        factor_id,p=ranked[rank-1]
        running=min(running, p*m/rank)
        out[factor_id]=min(1.0,running)
    return out
