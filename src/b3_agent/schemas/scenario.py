from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

AS_OF = date | datetime


@dataclass(frozen=True)
class ScenarioDefinition:
    """Deterministic scenario input; shocks are explicit assumptions, never predictions."""

    scenario_id: str
    name: str
    as_of: AS_OF
    ticker_price_shocks: dict[str, float] = field(default_factory=dict)
    position_value_shocks: dict[str, float] = field(default_factory=dict)
    fx_shocks: dict[str, float] = field(default_factory=dict)
    rate_shocks_bps: dict[str, float] = field(default_factory=dict)
    commodity_shocks: dict[str, float] = field(default_factory=dict)
    volatility_shocks: dict[str, float] = field(default_factory=dict)
    assumptions: dict[str, Any] = field(default_factory=dict)
    source_refs: tuple[str, ...] = ()
    schema_version: str = "1.0"

    def __post_init__(self) -> None:
        if not self.scenario_id.strip():
            raise ValueError("scenario_id must be non-empty")
        if not self.name.strip():
            raise ValueError("name must be non-empty")
        for mapping_name, mapping in (
            ("ticker_price_shocks", self.ticker_price_shocks),
            ("position_value_shocks", self.position_value_shocks),
            ("fx_shocks", self.fx_shocks),
            ("commodity_shocks", self.commodity_shocks),
            ("volatility_shocks", self.volatility_shocks),
        ):
            for key, value in mapping.items():
                if not str(key).strip():
                    raise ValueError(f"{mapping_name} keys must be non-empty")
                if value <= -1.0:
                    raise ValueError(f"{mapping_name} shocks must be greater than -100%")
        for key in self.rate_shocks_bps:
            if not str(key).strip():
                raise ValueError("rate_shocks_bps keys must be non-empty")


@dataclass(frozen=True)
class PositionStress:
    position_id: str
    ticker: str
    base_value: float
    stressed_value: float
    pnl_impact: float
    applied_shock: float


@dataclass(frozen=True)
class StressResult:
    scenario_id: str
    as_of: AS_OF
    base_portfolio_value: float
    stressed_portfolio_value: float
    portfolio_pnl: float
    portfolio_return: float | None
    cash: float
    assignment_capital: float
    cash_after_assignment: float
    max_concentration: float
    gross_exposure: float
    position_stress: tuple[PositionStress, ...] = ()
    sensitivities: dict[str, float] = field(default_factory=dict)
    assumptions: dict[str, Any] = field(default_factory=dict)
    source_refs: tuple[str, ...] = ()
    quality_status: str = "VALIDATED"
    schema_version: str = "1.0"

    def __post_init__(self) -> None:
        if self.quality_status not in {"VALIDATED", "WARNING", "REJECTED"}:
            raise ValueError("invalid quality_status")
