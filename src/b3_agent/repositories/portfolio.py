from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from b3_agent.schemas.position import PortfolioContext, Position


class PortfolioRepository:
    """Load a normalized portfolio snapshot from an explicit JSON source.

    The repository is intentionally file-backed for the MCP MVP. It never
    invents portfolio data: a missing or malformed source is an explicit error.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser().resolve()

    def load(self) -> PortfolioContext:
        if not self.path.exists():
            raise FileNotFoundError(
                f"Portfolio source not found: {self.path}. "
                "Set B3_AGENT_PORTFOLIO_FILE or create data/portfolio.json."
            )

        if self.path.suffix.lower() != ".json":
            raise ValueError("Portfolio MCP source must be a JSON file for MVP v0.1")

        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid portfolio JSON: {self.path}") from exc

        if not isinstance(payload, dict):
            raise ValueError("Portfolio JSON root must be an object")

        as_of = _parse_date(payload.get("as_of"), "as_of")
        positions_payload = payload.get("positions")
        if not isinstance(positions_payload, list):
            raise ValueError("Portfolio JSON must contain a 'positions' list")

        positions = tuple(_parse_position(item) for item in positions_payload)
        source_refs = tuple(str(value) for value in payload.get("source_refs", ()))
        quality_status = str(payload.get("quality_status", "VALIDATED"))
        cash = float(payload.get("cash", 0.0))

        return PortfolioContext(
            as_of=as_of,
            positions=positions,
            cash=cash,
            source_refs=source_refs,
            quality_status=quality_status,
        )


def _parse_position(payload: Any) -> Position:
    if not isinstance(payload, dict):
        raise ValueError("Each portfolio position must be an object")

    expiration_date = payload.get("expiration_date")
    return Position(
        position_id=str(payload["position_id"]),
        ticker=str(payload["ticker"]),
        instrument_type=str(payload["instrument_type"]),
        quantity=float(payload["quantity"]),
        average_cost=_optional_float(payload.get("average_cost")),
        strike=_optional_float(payload.get("strike")),
        expiration_date=(
            _parse_date(expiration_date, "expiration_date")
            if expiration_date is not None
            else None
        ),
        option_type=(
            str(payload["option_type"])
            if payload.get("option_type") is not None
            else None
        ),
        underlying_ticker=(
            str(payload["underlying_ticker"])
            if payload.get("underlying_ticker") is not None
            else None
        ),
        contract_multiplier=float(payload.get("contract_multiplier", 1.0)),
        market_price=_optional_float(payload.get("market_price")),
        market_value=_optional_float(payload.get("market_value")),
        source_ref=str(payload.get("source_ref", "")),
    )


def _parse_date(value: Any, field_name: str) -> date:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be an ISO date string")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an ISO date string") from exc


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)
