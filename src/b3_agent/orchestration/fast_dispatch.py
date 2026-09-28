from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import re
from typing import Any

from b3_agent.config import settings
from b3_agent.orchestration.contracts import OrchestratorResponse
from b3_agent.orchestration.live_providers import LiveProviderService
from b3_agent.portfolio.context import PortfolioIntelligenceEngine
from b3_agent.portfolio.pnl import PnlEngine
from b3_agent.portfolio.snapshot import load_active_snapshots
from b3_agent.routing import FastRouter, RouteDecision, RouteTarget
from b3_agent.scenario import ScenarioStressEngine
from b3_agent.schemas.position import PortfolioContext
from b3_agent.schemas.scenario import ScenarioDefinition


_PERCENT_RE = re.compile(r"(?P<value>[+-]?\d+(?:[\.,]\d+)?)\s*%")


class FastRouteDispatcher:
    """Execute V4.1 deterministic routes before the senior LLM workflow.

    Returning None means the request must be escalated to the existing
    OpenClaw-backed reasoning workflow. Deterministic routes never invoke an
    LLM and never infer missing financial facts.
    """

    def __init__(self, router: FastRouter | None = None) -> None:
        self.router = router or FastRouter()

    def dispatch(
        self,
        *,
        task: str,
        ticker: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> OrchestratorResponse | None:
        metadata = dict(context or {})
        if ticker:
            metadata.setdefault("ticker", ticker.upper().strip())

        decision = self.router.route(
            task,
            source=str(metadata.get("source") or "user"),
            task_type=(
                str(metadata["task_type"])
                if metadata.get("task_type") is not None
                else None
            ),
            metadata=metadata,
        )

        if decision.target == RouteTarget.OPENCLAW:
            return None
        if decision.target == RouteTarget.PORTFOLIO_ENGINE:
            return self._portfolio_snapshot(decision)
        if decision.target == RouteTarget.OPTIONS_ENGINE:
            return self._options_snapshot(decision, task)
        if decision.target == RouteTarget.MARKET_PROVIDER:
            return self._market_snapshot(decision)
        if decision.target == RouteTarget.STRESS_ENGINE:
            return self._stress_snapshot(decision, task)

        return None

    @staticmethod
    def _portfolio() -> PortfolioContext:
        snapshots = load_active_snapshots(settings.data_dir)
        portfolio = snapshots.get("portfolio_context")
        if not isinstance(portfolio, PortfolioContext):
            raise RuntimeError(
                "No active canonical portfolio snapshot is available; "
                "import a validated portfolio.xlsx first"
            )
        return portfolio

    def _portfolio_snapshot(self, decision: RouteDecision) -> OrchestratorResponse:
        portfolio = self._portfolio()
        intelligence = PortfolioIntelligenceEngine().build(portfolio)
        pnl_rows = self._position_pnl(portfolio)
        return self._response(
            decision,
            status="COMPLETED",
            result={
                "as_of": portfolio.as_of,
                "quality_status": portfolio.quality_status,
                "portfolio_context": asdict(portfolio),
                "portfolio_intelligence": asdict(intelligence),
                "position_pnl": pnl_rows,
                "limitations": (
                    []
                    if len(pnl_rows) == len(portfolio.positions)
                    else [
                        "P&L is returned only for positions with both average_cost and market_price; missing values are not inferred."
                    ]
                ),
            },
            sources=portfolio.source_refs,
        )

    def _options_snapshot(
        self,
        decision: RouteDecision,
        task: str,
    ) -> OrchestratorResponse:
        portfolio = self._portfolio()
        held_options = [
            position
            for position in portfolio.positions
            if position.instrument_type.upper() == "OPTION"
        ]

        option_rows: list[dict[str, Any]] = []
        for position in held_options:
            row = asdict(position)
            row["dte"] = (
                (position.expiration_date - portfolio.as_of).days
                if position.expiration_date is not None
                else None
            )
            option_rows.append(row)

        result: dict[str, Any] = {
            "as_of": portfolio.as_of,
            "quality_status": portfolio.quality_status,
            "option_positions": option_rows,
            "option_position_count": len(option_rows),
            "limitations": [],
        }
        sources = list(portfolio.source_refs)

        ticker = decision.metadata.get("ticker")
        wants_live_metrics = bool(
            ticker
            and any(
                token in task.lower()
                for token in (
                    "greek",
                    "delta",
                    "gamma",
                    "theta",
                    "vega",
                    "rho",
                    "iv",
                    "volatilidade implícita",
                    "volatilidade implicita",
                )
            )
        )

        if wants_live_metrics:
            snapshot = LiveProviderService().load(str(ticker))
            held_ids = {
                position.ticker.upper()
                for position in held_options
                if (position.underlying_ticker or position.ticker).upper()
                == str(ticker).upper()
            }
            live_metrics = [
                asdict(quote)
                for quote in snapshot.option_quotes
                if quote.option_id.upper() in held_ids
            ]
            result["live_option_metrics"] = live_metrics
            result["live_metrics_as_of"] = snapshot.as_of
            if not live_metrics:
                result["limitations"].append(
                    "No current OPLAB quote matched the held option identifiers."
                )
            sources.extend(snapshot.source_refs)

        return self._response(
            decision,
            status="COMPLETED",
            result=result,
            sources=tuple(dict.fromkeys(sources)),
        )

    def _market_snapshot(self, decision: RouteDecision) -> OrchestratorResponse:
        ticker = str(decision.metadata.get("ticker") or "").upper().strip()
        if not ticker:
            raise ValueError("market lookup requires an explicit B3 ticker")

        service = LiveProviderService()
        end = datetime.now(timezone.utc).date()
        start = end - timedelta(days=14)
        records = tuple(service.market_provider.get_market_data(ticker, start, end))
        if not records:
            raise RuntimeError(f"No market data available for {ticker}")

        latest = max(records, key=lambda item: item.observation_timestamp)
        return self._response(
            decision,
            status="COMPLETED",
            result={
                "ticker": ticker,
                "as_of": latest.observation_timestamp,
                "quality_status": "VALIDATED",
                "latest_daily_market_record": asdict(latest),
                "history_count": len(records),
                "limitations": [
                    "This deterministic route returns the latest available daily record; it does not infer an intraday quote."
                ],
            },
            sources=tuple(dict.fromkeys(item.source for item in records)),
        )

    def _stress_snapshot(
        self,
        decision: RouteDecision,
        task: str,
    ) -> OrchestratorResponse:
        portfolio = self._portfolio()
        baseline = PortfolioIntelligenceEngine().build(portfolio)
        context = decision.metadata

        ticker_shocks = self._shock_map(context.get("ticker_price_shocks"))
        position_shocks = self._shock_map(context.get("position_value_shocks"))

        if not ticker_shocks and not position_shocks:
            explicit_ticker = str(context.get("ticker") or "").upper().strip()
            percent = self._extract_percent(task)
            if explicit_ticker and percent is not None:
                ticker_shocks[explicit_ticker] = percent

        if not ticker_shocks and not position_shocks:
            return self._response(
                decision,
                status="LIMITED",
                result={
                    "as_of": portfolio.as_of,
                    "quality_status": "LIMITED",
                    "baseline_portfolio_intelligence": asdict(baseline),
                    "scenario_result": None,
                    "limitations": [
                        "No explicit position or B3 ticker shock was supplied.",
                        "An index move such as IBOV -10% is not automatically translated into position shocks because beta/option repricing must not be inferred.",
                    ],
                },
                sources=portfolio.source_refs,
            )

        scenario = ScenarioDefinition(
            scenario_id=f"FAST-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            name="Fast Router explicit stress",
            as_of=portfolio.as_of,
            ticker_price_shocks=ticker_shocks,
            position_value_shocks=position_shocks,
            assumptions={
                "origin": "fast_router",
                "option_repricing": "not_inferred",
            },
            source_refs=portfolio.source_refs,
        )
        stress = ScenarioStressEngine().evaluate(portfolio, scenario)
        return self._response(
            decision,
            status="COMPLETED",
            result={
                "as_of": portfolio.as_of,
                "quality_status": stress.quality_status,
                "baseline_portfolio_intelligence": asdict(baseline),
                "scenario_result": asdict(stress),
            },
            sources=tuple(dict.fromkeys((*portfolio.source_refs, *stress.source_refs))),
        )

    @staticmethod
    def _position_pnl(portfolio: PortfolioContext) -> list[dict[str, Any]]:
        engine = PnlEngine()
        rows: list[dict[str, Any]] = []
        for position in portfolio.positions:
            if position.average_cost is None or position.market_price is None:
                continue
            if position.instrument_type.upper() == "OPTION":
                pnl = engine.option_from_quotes(
                    position_id=position.position_id,
                    quantity=position.quantity,
                    opening_price=position.average_cost,
                    current_price=position.market_price,
                    contract_multiplier=position.contract_multiplier,
                )
            else:
                pnl = engine.stock_unrealized(
                    position_id=position.position_id,
                    quantity=position.quantity,
                    average_cost=position.average_cost,
                    market_price=position.market_price,
                )
            rows.append(asdict(pnl))
        return rows

    @staticmethod
    def _shock_map(value: Any) -> dict[str, float]:
        if not isinstance(value, dict):
            return {}
        shocks: dict[str, float] = {}
        for key, raw in value.items():
            normalized_key = str(key).upper().strip()
            if not normalized_key:
                continue
            shocks[normalized_key] = float(raw)
        return shocks

    @staticmethod
    def _extract_percent(text: str) -> float | None:
        match = _PERCENT_RE.search(text)
        if match is None:
            return None
        return float(match.group("value").replace(",", ".")) / 100.0

    @staticmethod
    def _response(
        decision: RouteDecision,
        *,
        status: str,
        result: dict[str, Any],
        sources: tuple[str, ...] = (),
    ) -> OrchestratorResponse:
        route = {
            "namespace": decision.namespace,
            "intent": decision.intent,
            "use_case": decision.use_case,
            "execution_mode": decision.execution_mode,
            "route": decision.route,
            "target": decision.target.value,
            "match": decision.match.value,
            "matched_rule": decision.matched_rule,
        }
        return OrchestratorResponse(
            status=status,
            result={"fast_route": route, **result},
            sources=sources,
            audit=(
                {
                    "event": "fast_router_dispatch",
                    **route,
                },
            ),
        )
