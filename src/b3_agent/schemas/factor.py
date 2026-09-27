from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

AS_OF = date | datetime


@dataclass(frozen=True)
class FactorObservation:
    observed_at: datetime
    factor_value: float
    forward_return: float


@dataclass(frozen=True)
class FactorTestResult:
    factor_id: str
    as_of: AS_OF
    sample_size: int
    train_size: int
    holdout_size: int
    train_correlation: float | None
    holdout_correlation: float | None
    t_statistic: float | None
    p_value: float | None
    adjusted_p_value: float | None
    statistically_significant: bool
    direction_stable: bool
    quality_status: str
    source_refs: tuple[str, ...] = ()
    interpretation: str = "association_only_no_causal_claim"


@dataclass(frozen=True)
class FactorStudy:
    as_of: AS_OF
    results: tuple[FactorTestResult, ...]
    correction_method: str = "BENJAMINI_HOCHBERG"
    alpha: float = 0.05
    holdout_fraction: float = 0.30
    min_sample_size: int = 30
    methodology: str = "time_ordered_holdout; factor_t predicts forward_return_t"


@dataclass(frozen=True)
class FactorWalkForwardFold:
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    train_correlation: float | None
    test_correlation: float | None
    direction_stable: bool


@dataclass(frozen=True)
class FactorWalkForwardResult:
    factor_id: str
    as_of: AS_OF
    folds: tuple[FactorWalkForwardFold, ...]
    stable_fold_ratio: float
    median_test_correlation: float | None
    quality_status: str
    interpretation: str = "association_only_no_causal_claim"
