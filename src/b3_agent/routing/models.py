from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class MatchClass(str, Enum):
    MATCH_EXACT = "MATCH_EXACT"
    MATCH_STRONG = "MATCH_STRONG"
    AMBIGUOUS = "AMBIGUOUS"


class RouteTarget(str, Enum):
    MARKET_PROVIDER = "market_provider"
    PORTFOLIO_ENGINE = "portfolio_engine"
    OPTIONS_ENGINE = "options_engine"
    STRESS_ENGINE = "stress_engine"
    STRATEGY_ENGINE = "strategy_engine"
    MACRO_JOB = "macro_job"
    DEEPSEEK_BACKGROUND = "deepseek-r1:8b"
    OPENCLAW = "openclaw"


@dataclass(frozen=True, slots=True)
class RouteDecision:
    namespace: str
    intent: str | None
    use_case: str | None
    execution_mode: str
    route: str
    target: RouteTarget
    match: MatchClass
    matched_rule: str | None
    metadata: dict[str, Any]
