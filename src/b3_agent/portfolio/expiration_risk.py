from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .position_intelligence import PositionAssessment


@dataclass(frozen=True)
class ExpirationRisk:
    expiration_date: date
    option_count: int
    short_put_count: int
    short_call_count: int
    assignment_capital: float
    deliverable_shares: float


def summarize_expiration_risk(
    assessments: tuple[PositionAssessment, ...],
) -> tuple[ExpirationRisk, ...]:
    buckets: dict[date, dict[str, float]] = {}
    for item in assessments:
        if item.instrument_type != "OPTION" or item.expiration_date is None:
            continue
        bucket = buckets.setdefault(
            item.expiration_date,
            {"option_count": 0, "short_put_count": 0, "short_call_count": 0,
             "assignment_capital": 0.0, "deliverable_shares": 0.0},
        )
        bucket["option_count"] += 1
        if item.side == "SHORT" and item.option_type == "PUT":
            bucket["short_put_count"] += 1
        if item.side == "SHORT" and item.option_type == "CALL":
            bucket["short_call_count"] += 1
        bucket["assignment_capital"] += item.assignment_capital
        bucket["deliverable_shares"] += item.deliverable_shares
    return tuple(
        ExpirationRisk(
            expiration_date=expiry,
            option_count=int(values["option_count"]),
            short_put_count=int(values["short_put_count"]),
            short_call_count=int(values["short_call_count"]),
            assignment_capital=values["assignment_capital"],
            deliverable_shares=values["deliverable_shares"],
        )
        for expiry, values in sorted(buckets.items())
    )
