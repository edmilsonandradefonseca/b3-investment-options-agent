from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
import math
import re
from statistics import NormalDist
from typing import Any, Protocol

from b3_agent.options.call import CallAnalysisEngine
from b3_agent.options.put import PutAnalysisEngine
from b3_agent.orchestration.live_providers import LiveProviderService
from b3_agent.portfolio.snapshot import load_active_snapshots
from b3_agent.providers.brapi.fundamentals import BrapiFundamentalsAdapter
from b3_agent.providers.oplab.adapter import OplabAdapter
from b3_agent.providers.oplab.options import OplabOptionsAdapter
from b3_agent.quant_engine import compute_quant_features
from b3_agent.schemas.position import PortfolioContext
from b3_agent.schemas.strategy_comparison import StrategyAlternative
from b3_agent.strategy_comparison import StrategyComparisonEngine


class MarketProvider(Protocol):
    @property
    def name(self) -> str: ...

    def get_market_data(self, ticker: str, start, end): ...


class FundamentalsProvider(Protocol):
    @property
    def name(self) -> str: ...

    def get_financial_data(self, ticker: str): ...


class CurrentQuoteProvider(Protocol):
    @property
    def name(self) -> str: ...

    def get_current_quote(self, ticker: str): ...


_B3_EQUITY_TICKER = re.compile(r"^[A-Z]{4}\d{1,2}$")


def _validated_equity_ticker(value: str) -> str:
    normalized = str(value).upper().strip()
    if not _B3_EQUITY_TICKER.fullmatch(normalized):
        raise ValueError(
            f"invalid B3 equity ticker {normalized!r}; expected four letters followed by one or two digits"
        )
    return normalized


@dataclass(frozen=True)
class AssetEvidencePack:
    """Compact deterministic evidence for one strategy-comparison asset.

    The pack intentionally contains observed/provider facts and deterministic
    quantitative features only. It does not invent valuation assumptions,
    expected returns, ranking weights, or an investment recommendation.
    """

    ticker: str
    as_of: datetime
    market: dict[str, Any]
    quant: dict[str, Any]
    fundamentals: dict[str, Any]
    portfolio: dict[str, Any]
    source_refs: tuple[str, ...]
    quality_status: str
    limitations: tuple[str, ...] = ()


class StrategyEvidenceService:
    """Build a compact multi-source evidence pack without invoking an LLM."""

    def __init__(
        self,
        *,
        market_provider: MarketProvider | None = None,
        fundamentals_provider: FundamentalsProvider | None = None,
        current_quote_provider: CurrentQuoteProvider | None = None,
        history_days: int = 120,
    ) -> None:
        if history_days < 1:
            raise ValueError("history_days must be positive")
        self.market_provider = market_provider or LiveProviderService().market_provider
        self.fundamentals_provider = (
            fundamentals_provider or BrapiFundamentalsAdapter()
        )
        self.current_quote_provider = current_quote_provider or OplabAdapter()
        self.history_days = history_days

    def build(
        self,
        ticker: str,
        *,
        as_of: datetime,
        portfolio: PortfolioContext | None = None,
    ) -> AssetEvidencePack:
        normalized = _validated_equity_ticker(ticker)
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")

        end = as_of.date()
        start = end - timedelta(days=self.history_days)
        market_records = tuple(
            self.market_provider.get_market_data(normalized, start, end)
        )
        if not market_records:
            raise ValueError(f"no market data returned for {normalized}")

        latest = max(
            market_records,
            key=lambda item: item.observation_timestamp,
        )
        quant = compute_quant_features(market_records, as_of=as_of)

        limitations: list[str] = []
        current_quote = None
        try:
            current_quote = self.current_quote_provider.get_current_quote(
                normalized
            )
        except (OSError, RuntimeError, ValueError) as exc:
            limitations.append(
                f"Current quote unavailable for {normalized}: {exc}"
            )
        previous_completed = None
        if current_quote is not None:
            current_session_date = current_quote.observation_timestamp.date()
            completed_rows = [
                row
                for row in market_records
                if row.observation_timestamp.date() < current_session_date
            ]
            if completed_rows:
                previous_completed = max(
                    completed_rows,
                    key=lambda item: item.observation_timestamp,
                )

        fundamental_rows = ()
        try:
            fundamental_rows = tuple(
                self.fundamentals_provider.get_financial_data(normalized)
            )
        except (OSError, RuntimeError, ValueError) as exc:
            limitations.append(
                f"Fundamentals unavailable for {normalized}: {exc}"
            )

        metrics = {
            row.metric: {
                "value": row.value,
                "unit": row.unit,
                "period_type": row.period_type,
                "report_date": row.report_date,
                "available_timestamp": row.available_timestamp,
                "quality_status": row.quality_status,
                "quality_flags": row.quality_flags,
                "source": row.source,
            }
            for row in fundamental_rows
        }

        matching_positions = ()
        if portfolio is not None:
            matching_positions = tuple(
                position
                for position in portfolio.positions
                if (
                    (
                        position.underlying_ticker
                        if position.instrument_type.upper() == "OPTION"
                        and position.underlying_ticker
                        else position.ticker
                    ).upper()
                    == normalized
                )
            )

        stock_quantity = sum(
            position.quantity
            for position in matching_positions
            if position.instrument_type.upper() == "STOCK"
        )
        known_market_values = [
            position.market_value
            for position in matching_positions
            if position.market_value is not None
        ]

        sources = tuple(
            dict.fromkeys(
                [
                    *(row.source for row in market_records if row.source),
                    *(
                        (current_quote.source,)
                        if current_quote is not None and current_quote.source
                        else ()
                    ),
                    *(row.source for row in fundamental_rows if row.source),
                    *(
                        portfolio.source_refs
                        if portfolio is not None and matching_positions
                        else ()
                    ),
                ]
            )
        )

        quality = "VALIDATED"
        if limitations or any(
            row.quality_status != "VALIDATED" for row in fundamental_rows
        ):
            quality = "WARNING"

        return AssetEvidencePack(
            ticker=normalized,
            as_of=as_of,
            market={
                "current_quote": (
                    asdict(current_quote)
                    if current_quote is not None
                    else None
                ),
                "current_quote_reuse": getattr(self.current_quote_provider, "last_reuse_telemetry", {}),
                "history_count": len(market_records),
                "history_latest": asdict(latest),
                "previous_completed_close": (
                    asdict(previous_completed)
                    if previous_completed is not None
                    else None
                ),
                # Backward-compatible alias; new consumers must use
                # current_quote for the actual current stock price.
                "latest": asdict(latest),
                "history_start": min(
                    row.observation_timestamp for row in market_records
                ),
                "history_end": max(
                    row.observation_timestamp for row in market_records
                ),
            },
            quant=asdict(quant),
            fundamentals={
                "metric_count": len(fundamental_rows),
                "metrics": metrics,
                "provider": self.fundamentals_provider.name,
            },
            portfolio={
                "held": bool(matching_positions),
                "position_count": len(matching_positions),
                "stock_quantity": stock_quantity,
                "known_market_value": (
                    sum(known_market_values) if known_market_values else None
                ),
                "snapshot_as_of": portfolio.as_of if portfolio is not None else None,
                "cash_is_known": (
                    portfolio.cash_is_known if portfolio is not None else None
                ),
            },
            source_refs=sources,
            quality_status=quality,
            limitations=tuple(limitations),
        )


class LiveStrategyComparisonService:
    """Compose UC-04 alternatives from live deterministic facts.

    BUY_STOCK and HOLD use the current OPLAB underlying quote plus historical
    evidence. SELL_PUT and covered SELL_CALL require an explicit OPLAB option
    identifier; the service never chooses an option contract silently.
    """

    _STRATEGY_ALIASES = {
        "comprar ação": "BUY_STOCK",
        "comprar acao": "BUY_STOCK",
        "buy stock": "BUY_STOCK",
        "buy_stock": "BUY_STOCK",
        "manter": "HOLD",
        "hold": "HOLD",
        "vender put": "SELL_PUT",
        "sell put": "SELL_PUT",
        "sell_put": "SELL_PUT",
        "vender call": "SELL_CALL",
        "vender call coberta": "SELL_CALL",
        "covered call": "SELL_CALL",
        "sell call": "SELL_CALL",
        "sell_call": "SELL_CALL",
        "vender ação": "SELL_STOCK",
        "vender acao": "SELL_STOCK",
        "vender/reduzir ação": "SELL_STOCK",
        "vender/reduzir acao": "SELL_STOCK",
        "reduzir ação": "SELL_STOCK",
        "reduzir acao": "SELL_STOCK",
        "sell stock": "SELL_STOCK",
        "sell_stock": "SELL_STOCK",
        "reduce stock": "SELL_STOCK",
        "reduce_stock": "SELL_STOCK",
    }

    def __init__(
        self,
        *,
        evidence_service: StrategyEvidenceService | None = None,
        comparison_engine: StrategyComparisonEngine | None = None,
        options_provider: OplabOptionsAdapter | None = None,
    ) -> None:
        self.evidence_service = evidence_service or StrategyEvidenceService()
        self.comparison_engine = comparison_engine or StrategyComparisonEngine()
        self.options_provider = options_provider or OplabOptionsAdapter()

    @classmethod
    def normalize_strategy(cls, value: str) -> str | None:
        return cls._STRATEGY_ALIASES.get(" ".join(value.casefold().split()))

    def compare_put_candidates(
        self,
        *,
        ticker: str,
        option_ids: tuple[str, ...] | list[str],
        scenario_horizon: date | str | None = None,
        scenario_shocks_pct: list[float] | tuple[float, ...] | None = None,
        scenario_objective: str = "COMPARE_ONLY",
        portfolio: PortfolioContext | None = None,
        as_of: datetime | None = None,
    ) -> dict[str, Any]:
        """Compare explicit same-expiry PUTs from one live option-chain snapshot."""
        normalized_ticker = _validated_equity_ticker(ticker)
        normalized_ids = tuple(str(item).upper().strip() for item in option_ids)
        if not 2 <= len(normalized_ids) <= 20:
            raise ValueError("PUT comparison requires between 2 and 20 explicit contracts")
        if any(not item for item in normalized_ids) or len(set(normalized_ids)) != len(normalized_ids):
            raise ValueError("PUT contract identifiers must be non-empty and unique")

        effective_as_of = as_of or datetime.now(timezone.utc)
        if effective_as_of.tzinfo is None or effective_as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        horizon = (
            date.fromisoformat(scenario_horizon)
            if isinstance(scenario_horizon, str) and scenario_horizon.strip()
            else scenario_horizon
        )
        shocks = tuple(scenario_shocks_pct or ())
        if len(shocks) > 9 or any(
            not isinstance(value, (int, float)) or not math.isfinite(value) or value < -90 or value > 300
            for value in shocks
        ) or len(set(shocks)) != len(shocks):
            raise ValueError("scenario shocks must be unique finite percentages from -90 to 300 (maximum nine)")
        objective = str(scenario_objective or "COMPARE_ONLY").upper().strip()
        if objective not in {"COMPARE_ONLY", "MAXIMIZE_WORST_CASE_RETURN_ON_CAPITAL"}:
            raise ValueError("unsupported explicit scenario objective")
        if shocks and horizon is None:
            raise ValueError("scenario horizon is required for explicit price scenarios")
        if horizon is not None and horizon <= effective_as_of.date():
            raise ValueError("scenario horizon must be after the comparison date")

        pack = self.evidence_service.build(normalized_ticker, as_of=effective_as_of, portfolio=portfolio)
        contracts, quotes = self.options_provider.get_snapshot(normalized_ticker, effective_as_of)
        by_id: dict[str, list[Any]] = {}
        quote_by_id: dict[str, list[Any]] = {}
        for contract in contracts:
            by_id.setdefault(contract.option_id.upper(), []).append(contract)
        for quote in quotes:
            quote_by_id.setdefault(quote.option_id.upper(), []).append(quote)

        selected: list[tuple[Any, Any]] = []
        for option_id in normalized_ids:
            matches = by_id.get(option_id, [])
            if len(matches) != 1:
                raise ValueError(f"{option_id} must identify exactly one current contract for {normalized_ticker}")
            contract = matches[0]
            if contract.underlying_ticker.upper() != normalized_ticker or contract.option_type.upper() != "PUT":
                raise ValueError(f"{option_id} is not an exact {normalized_ticker} PUT contract")
            if contract.expiration_date <= effective_as_of.date():
                raise ValueError(f"{option_id} is expired or expires today")
            matched_quotes = quote_by_id.get(option_id, [])
            if len(matched_quotes) != 1:
                raise ValueError(f"{option_id} must have exactly one quote in the same current chain snapshot")
            quote = matched_quotes[0]
            if quote.bid is None or quote.bid <= 0:
                raise ValueError(f"{option_id} has no executable current bid")
            if as_of is not None and (
                quote.observation_timestamp > effective_as_of
                or quote.available_timestamp > effective_as_of
            ):
                raise ValueError(f"{option_id} quote was not observable and available at the requested as_of")
            selected.append((contract, quote))

        expirations = {contract.expiration_date for contract, _ in selected}
        if len(expirations) != 1:
            raise ValueError("selected PUT contracts must share one exact expiration date")
        expiration = next(iter(expirations))
        if shocks and horizon != expiration:
            raise ValueError("PUT terminal scenarios require a horizon equal to the selected contracts' expiration")
        underlying = pack.market.get("current_quote")
        if as_of is not None and isinstance(underlying, dict):
            for timestamp_field in ("observation_timestamp", "available_timestamp"):
                timestamp = underlying.get(timestamp_field)
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                if isinstance(timestamp, datetime) and timestamp > effective_as_of:
                    raise ValueError(f"underlying quote was not observable and available at the requested as_of")
        spot = (
            float(underlying["close"])
            if isinstance(underlying, dict)
            and isinstance(underlying.get("close"), (int, float))
            and float(underlying["close"]) > 0
            else None
        )
        days_to_expiration = (expiration - effective_as_of.date()).days
        candidates: list[dict[str, Any]] = []
        source_refs = list(pack.source_refs)
        for contract, quote in sorted(selected, key=lambda row: (row[0].strike, row[0].option_id)):
            multiplier = float(contract.contract_multiplier)
            premium = float(quote.bid)
            break_even = float(contract.strike) - premium
            probability = _put_model_probabilities(
                spot=spot, strike=float(contract.strike), volatility=quote.implied_volatility,
                days=days_to_expiration,
            )
            raw_style = str(contract.exercise_style or "").strip()
            style = _normalize_exercise_style(raw_style)
            payoff_by_scenario: dict[str, float] = {}
            if shocks and horizon == expiration and spot is not None:
                for shock in shocks:
                    scenario_id = f"{horizon.isoformat()}:{shock:g}%"
                    terminal = spot * (1 + shock / 100)
                    pnl = (premium - max(float(contract.strike) - terminal, 0.0)) * multiplier
                    payoff_by_scenario[scenario_id] = round(pnl, 8)
            spread = float(quote.ask) - premium if quote.ask is not None and quote.ask >= premium else None
            source_refs.extend([quote.source, contract.option_ticker])
            candidates.append({
                "contract": asdict(contract),
                "quote": asdict(quote),
                "premium_per_share_at_bid": premium,
                "premium_total_one_contract": premium * multiplier,
                "capital_required_one_contract": float(contract.strike) * multiplier,
                "maximum_loss_one_contract_before_costs": break_even * multiplier,
                "breakeven_price": break_even,
                "spread_abs": spread,
                "spread_pct_of_mid": spread / quote.mid if spread is not None and quote.mid and quote.mid > 0 else None,
                "volume": quote.volume,
                "open_interest": quote.open_interest,
                "days_to_expiration": days_to_expiration,
                "probability_estimates": {
                    **probability,
                    "source": "current chain implied volatility" if probability["expiry_itm_probability"] is not None else None,
                    "model": "risk-neutral lognormal proxy; zero rate and zero carry assumptions",
                    "as_of": quote.observation_timestamp.isoformat(),
                    "calibration_status": "NOT_CALIBRATED",
                    "not_personal_frequency": True,
                },
                "exercise_style": {"raw": raw_style or None, "normalized": style, "status": "PROVIDER_REPORTED" if style else "UNKNOWN"},
                "early_assignment": {
                    "status": "NOT_APPLICABLE_BY_PROVIDER_REPORTED_EUROPEAN_STYLE" if style == "EUROPEAN" else "UNKNOWN",
                    "reason": "American early-exercise behavior is not modeled; provider-reported style is not independently verified." if style != "EUROPEAN" else "OPLAB reports European style; this is a provider field, not independent legal verification.",
                },
                "personal_assignment_frequency": {
                    "status": "UNKNOWN", "numerator": None, "eligible_denominator": None,
                    "reason": "No eligible, PIT-comparable personal outcomes are supplied to this chain comparison.",
                },
                "pnl_by_scenario_brl": payoff_by_scenario,
                "return_by_scenario_pct": {
                    key: round(value / (float(contract.strike) * multiplier) * 100, 8)
                    for key, value in payoff_by_scenario.items()
                },
            })

        ranking: dict[str, Any] = {
            "requested_objective": objective,
            "status": "NOT_REQUESTED" if objective == "COMPARE_ONLY" else "UNAVAILABLE",
            "ranked_option_id": None, "tie_option_ids": [],
            "metric": "MAXIMIZE_MINIMUM_USER_SCENARIO_RETURN_ON_COLLATERAL", "not_a_forecast": True,
        }
        expected = {f"{horizon.isoformat()}:{shock:g}%" for shock in shocks} if horizon else set()
        if objective != "COMPARE_ONLY":
            complete = bool(expected) and all(
                set(candidate["pnl_by_scenario_brl"]) == expected
                and candidate["capital_required_one_contract"] > 0 for candidate in candidates
            )
            if complete:
                scores = [min(candidate["return_by_scenario_pct"].values()) for candidate in candidates]
                best = max(scores)
                winners = [candidate["contract"]["option_id"] for candidate, score in zip(candidates, scores, strict=True) if abs(score - best) <= 1e-9]
                ranking["status"] = "TIE" if len(winners) > 1 else "CONDITIONAL_RANKING"
                ranking["ranked_option_id"] = winners[0] if len(winners) == 1 else None
                ranking["tie_option_ids"] = winners if len(winners) > 1 else []
                ranking["worst_case_return_pct_by_option"] = {
                    candidate["contract"]["option_id"]: round(score, 8)
                    for candidate, score in zip(candidates, scores, strict=True)
                }
            else:
                ranking["reason"] = "Every candidate needs complete P&L for every explicit shock and known positive strike collateral."
        source_refs = list(dict.fromkeys(source_refs))
        return {
            "as_of": effective_as_of.isoformat(),
            "quality_status": pack.quality_status,
            "summary": f"Comparação de {len(candidates)} PUTs explícitas de {normalized_ticker}, vencimento {expiration.isoformat()}; sem ranking automático.",
            "put_chain_comparison": {
                "policy_version": "put-chain-comparison-v1", "ticker": normalized_ticker,
                "underlying_price": spot,
                "underlying_quote_as_of": underlying.get("observation_timestamp") if isinstance(underlying, dict) else None,
                "expiration_date": expiration.isoformat(),
                "quote_snapshot_as_of": max(quote.observation_timestamp for _, quote in selected).isoformat(),
                "candidate_count": len(candidates), "ranking": ranking,
                "probability_semantics": "Separate uncalibrated model estimates for expiry ITM and first touch; early assignment and personal frequency have separate fields.",
                "limitations": [
                    "Premium uses the current bid for one contract; fees, taxes, slippage and financing are excluded.",
                    "Expiry ITM/touch values are uncalibrated model estimates, not real-world probabilities or personal outcomes.",
                    "Personal assignment frequency remains UNKNOWN without eligible comparable outcomes and PIT entry evidence.",
                    "No selected contract is silently substituted; this comparison reads one chain snapshot.",
                ],
                "candidates": candidates,
            },
            "asset_evidence": {pack.ticker: asdict(pack)},
            "source_refs": source_refs,
        }

    @classmethod
    def supports(
        cls,
        values: tuple[str, str],
        *,
        option_ids: tuple[str | None, str | None] = (None, None),
    ) -> bool:
        if len(values) != 2 or len(option_ids) != 2:
            return False
        for strategy, option_id in zip(values, option_ids, strict=True):
            normalized = cls.normalize_strategy(strategy)
            if normalized is None:
                return False
            if normalized in {"SELL_PUT", "SELL_CALL"} and not str(option_id or "").strip():
                return False
        return True

    def compare(
        self,
        *,
        assets: tuple[str, str],
        strategies: tuple[str, str],
        option_ids: tuple[str | None, str | None] = (None, None),
        amount: float | None = None,
        scenario_horizon: date | str | None = None,
        scenario_shocks_pct: list[float] | tuple[float, ...] | None = None,
        scenario_objective: str = "COMPARE_ONLY",
        put_objective: str = "COMPARE_ONLY",
        economic_inputs: dict[str, Any] | None = None,
        portfolio: PortfolioContext | None = None,
        as_of: datetime | None = None,
    ) -> dict[str, Any]:
        if len(assets) != 2 or len(strategies) != 2 or len(option_ids) != 2:
            raise ValueError(
                "strategy comparison requires exactly two alternatives"
            )
        assets = tuple(_validated_equity_ticker(value) for value in assets)
        if amount is not None and amount < 0:
            raise ValueError("comparison amount must be non-negative")

        horizon = (
            date.fromisoformat(scenario_horizon)
            if isinstance(scenario_horizon, str) and scenario_horizon.strip()
            else scenario_horizon
        )
        shocks = tuple(scenario_shocks_pct or ())
        if len(shocks) > 9:
            raise ValueError("at most nine explicit price scenarios are supported")
        if any(
            not isinstance(shock, (int, float))
            or not math.isfinite(shock)
            or shock < -90
            or shock > 300
            for shock in shocks
        ):
            raise ValueError("scenario shocks must be finite percentages from -90 to 300")
        if len(set(shocks)) != len(shocks):
            raise ValueError("scenario shocks must be unique")
        normalized_objective = str(scenario_objective or "COMPARE_ONLY").upper().strip()
        if normalized_objective not in {
            "COMPARE_ONLY",
            "MAXIMIZE_WORST_CASE_RETURN_ON_CAPITAL",
        }:
            raise ValueError("unsupported explicit scenario objective")
        if shocks and horizon is None:
            raise ValueError("scenario horizon is required for explicit price scenarios")
        if horizon is not None and horizon <= (as_of.date() if as_of else datetime.now(timezone.utc).date()):
            raise ValueError("scenario horizon must be after the comparison date")

        normalized_strategies = tuple(
            self.normalize_strategy(value) for value in strategies
        )
        if any(value is None for value in normalized_strategies):
            raise ValueError(
                "live deterministic comparison supports BUY_STOCK, HOLD, SELL_STOCK, SELL_PUT and covered SELL_CALL"
            )
        if not self.supports(strategies, option_ids=option_ids):
            raise ValueError(
                "SELL_PUT/SELL_CALL require an explicit current OPLAB option identifier"
            )

        effective_as_of = as_of or datetime.now(timezone.utc)
        if effective_as_of.tzinfo is None or effective_as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")

        if economic_inputs is not None and normalized_strategies != ('BUY_STOCK','BUY_STOCK'):
            raise ValueError('Economic stock scenarios require two BUY_STOCK alternatives')
        is_put_pair = normalized_strategies == ('SELL_PUT','SELL_PUT')
        if put_objective not in {'COMPARE_ONLY','LOWEST_MODEL_EXPIRY_ITM','HIGHEST_GROSS_PREMIUM_PER_CAPITAL_30D'} or (not is_put_pair and put_objective != 'COMPARE_ONLY'):
            raise ValueError('A two-PUT objective requires exactly two PUT sale alternatives')
        prefetched_options = {}
        if is_put_pair:
            if as_of is not None:
                raise ValueError('Two-PUT comparison requires current chain evidence; historical contract availability is not established')
            if str(option_ids[0]).upper().strip() == str(option_ids[1]).upper().strip():
                raise ValueError('Select two distinct PUT contract identifiers')
            from b3_agent.opportunity_screen import StockOpportunityScreenService
            screen = StockOpportunityScreenService(self.evidence_service).build(assets, portfolio=portfolio, as_of=as_of)
            for ticker in dict.fromkeys(assets):
                prefetched_options[ticker] = self.options_provider.get_snapshot(ticker,effective_as_of)
            effective_as_of = as_of or datetime.now(timezone.utc)
            packs = tuple(AssetEvidencePack(**{**screen['asset_evidence'][ticker], 'as_of':effective_as_of}) for ticker in assets)
        else:
            packs = tuple(
                self.evidence_service.build(
                    ticker,
                    as_of=effective_as_of,
                    portfolio=portfolio,
                )
                for ticker in assets
            )

        target_evidence = {}
        dividend_evidence = {}
        if normalized_strategies == ("BUY_STOCK", "BUY_STOCK") and as_of is None:
            # Reuse the configured fundamentals adapter; failures are per-asset.
            from concurrent.futures import ThreadPoolExecutor
            getter = getattr(self.evidence_service.fundamentals_provider, "get_dividends", None)
            def collect_dividends(ticker):
                if getter is None:
                    return {"status": "UNSUPPORTED_PROVIDER", "records": []}
                try:
                    return {"status": "READ_OK", "records": [asdict(row) for row in getter(ticker, start=datetime.now(timezone.utc).date()-timedelta(days=366))]}
                except (OSError, RuntimeError, ValueError) as exc:
                    return {"status": "PROVIDER_UNAVAILABLE", "records": [], "error_type": type(exc).__name__, "http_status": getattr(exc, "code", None)}
            with ThreadPoolExecutor(max_workers=2) as executor:
                tickers = tuple(dict.fromkeys(assets))
                dividend_evidence = dict(zip(tickers, executor.map(collect_dividends, tickers), strict=True))

        # Current BUY evidence is acquired before freezing the decision cutoff.
        # Explicit historical cutoffs remain authoritative and are never advanced.
        if normalized_strategies == ("BUY_STOCK", "BUY_STOCK") and as_of is None:
            effective_as_of = datetime.now(timezone.utc)
            packs = tuple(AssetEvidencePack(**{**asdict(pack), "as_of": effective_as_of}) for pack in packs)

        alternatives: list[StrategyAlternative] = []
        option_evidence: dict[str, dict[str, Any]] = {}
        option_snapshots: dict[str, tuple[list[Any], list[Any]]] = prefetched_options
        all_sources: list[str] = [
            source for pack in packs for source in pack.source_refs
        ]

        for index, (pack, original, normalized_strategy, option_id) in enumerate(
            zip(
                packs,
                strategies,
                normalized_strategies,
                option_ids,
                strict=True,
            ),
            start=1,
        ):
            assert normalized_strategy is not None
            assumptions: dict[str, Any] = {
                "amount": amount,
                "expected_return": "not_inferred",
                "valuation": "not_computed_without_explicit_assumptions",
                "ranking": "not_applied",
                "current_underlying_quote": pack.market.get("current_quote"),
            }
            capital_required = (
                amount if normalized_strategy == "BUY_STOCK" else 0.0
            )
            max_loss = None
            subject_id = pack.ticker
            label = f"{original} · {pack.ticker}"
            alternative_sources = list(pack.source_refs)
            option_contract = None
            option_quote = None

            if normalized_strategy == "SELL_STOCK":
                if amount is None or amount <= 0:
                    raise ValueError(
                        "SELL_STOCK requires an explicit positive comparison amount"
                    )
                current_quote = pack.market.get("current_quote")
                current_price = (
                    float(current_quote.get("close"))
                    if isinstance(current_quote, dict)
                    and isinstance(current_quote.get("close"), (int, float))
                    else None
                )
                if current_price is None or current_price <= 0:
                    raise ValueError(
                        f"{pack.ticker} current OPLAB price is required for SELL_STOCK"
                    )
                stock_quantity = float(pack.portfolio.get("stock_quantity") or 0.0)
                if stock_quantity <= 0:
                    raise ValueError(
                        f"SELL_STOCK requires an existing long {pack.ticker} position"
                    )
                position_value = current_price * stock_quantity
                if amount > position_value + 1e-9:
                    raise ValueError(
                        f"SELL_STOCK amount {amount:.2f} exceeds current long "
                        f"position value {position_value:.2f} for {pack.ticker}"
                    )
                theoretical_shares_reduced = amount / current_price
                capital_required = 0.0
                assumptions.update({
                    "capital_released": amount,
                    "notional_reduction": amount,
                    "current_price_basis": "current_oplab_quote",
                    "stock_quantity_before": stock_quantity,
                    "theoretical_shares_reduced": theoretical_shares_reduced,
                    "stock_quantity_after_theoretical": (
                        stock_quantity - theoretical_shares_reduced
                    ),
                    "position_value_before": position_value,
                    "position_value_after_theoretical": (
                        position_value - amount
                    ),
                    "execution_quantity": "not_inferred",
                    "taxes_and_fees": "not_inferred",
                })

            if normalized_strategy in {"SELL_PUT", "SELL_CALL"}:
                normalized_option = str(option_id or "").upper().strip()
                if pack.ticker not in option_snapshots:
                    option_snapshots[pack.ticker] = self.options_provider.get_snapshot(
                        pack.ticker,
                        effective_as_of,
                    )
                contracts, quotes = option_snapshots[pack.ticker]
                contract = next(
                    (
                        item
                        for item in contracts
                        if item.option_id.upper() == normalized_option
                    ),
                    None,
                )
                quote = next(
                    (
                        item
                        for item in quotes
                        if item.option_id.upper() == normalized_option
                    ),
                    None,
                )
                if contract is None:
                    raise ValueError(
                        f"OPLAB contract {normalized_option} was not found for {pack.ticker}"
                    )
                expected_type = "PUT" if normalized_strategy == "SELL_PUT" else "CALL"
                if contract.option_type.upper() != expected_type:
                    raise ValueError(
                        f"{normalized_option} is not a {expected_type} contract"
                    )
                if contract.expiration_date <= effective_as_of.date():
                    raise ValueError(
                        f"{normalized_option} is expired or expires today"
                    )
                if quote is None:
                    raise ValueError(
                        f"OPLAB current quote {normalized_option} was not found"
                    )
                if quote.bid is None or quote.bid <= 0:
                    raise ValueError(
                        f"{normalized_option} has no executable current bid"
                    )
                if is_put_pair:
                    if sum(item.option_id.upper()==normalized_option for item in contracts)!=1 or sum(item.option_id.upper()==normalized_option for item in quotes)!=1:
                        raise ValueError('Each selected PUT must have exactly one contract and quote')
                    if contract.underlying_ticker.upper()!=pack.ticker or quote.ticker.upper()!=pack.ticker:
                        raise ValueError('PUT contract/quote identity does not match the selected underlying')
                    if (effective_as_of.date()-quote.observation_timestamp.date()).days>7:
                        raise ValueError('PUT quote is older than the seven-calendar-day policy')
                    if quote.observation_timestamp>effective_as_of or quote.available_timestamp>effective_as_of or quote.quality_status in {'REJECTED','INVALID'} or not quote.source:
                        raise ValueError('PUT quote is not admissible at the common PIT cutoff')
                    if any(not math.isfinite(float(value)) or float(value)<=0 for value in (contract.strike,contract.contract_multiplier,quote.bid)) or quote.bid>=contract.strike:
                        raise ValueError('Invalid PUT strike, multiplier or premium')
                option_contract = contract
                option_quote = quote

                subject_id = contract.option_id
                label = f"{original} {contract.option_id} · {pack.ticker}"
                spread_abs = (
                    quote.ask - quote.bid
                    if quote.bid is not None
                    and quote.ask is not None
                    and quote.ask >= quote.bid
                    else None
                )
                spread_pct_of_mid = (
                    spread_abs / quote.mid
                    if spread_abs is not None
                    and quote.mid is not None
                    and quote.mid > 0
                    else None
                )
                marketability = {
                    "executable_for_sell": quote.bid is not None and quote.bid > 0,
                    "two_sided_market": (
                        quote.bid is not None
                        and quote.bid > 0
                        and quote.ask is not None
                        and quote.ask > 0
                    ),
                    "volume_reported": quote.volume is not None and quote.volume > 0,
                    "open_interest_reported": (
                        quote.open_interest is not None
                        and quote.open_interest > 0
                    ),
                    "spread_abs": spread_abs,
                    "spread_pct_of_mid": spread_pct_of_mid,
                    "liquidity_score": None,
                    "liquidity_assessment": "not_scored_without_versioned_policy",
                }
                assumptions["option_marketability"] = marketability

                if normalized_strategy == "SELL_PUT":
                    put = PutAnalysisEngine().analyze(
                        option_id=contract.option_id,
                        underlying_ticker=pack.ticker,
                        strike=contract.strike,
                        expiration_date=contract.expiration_date,
                        premium=quote.bid,
                        contract_multiplier=contract.contract_multiplier,
                        as_of=effective_as_of.date(),
                    )
                    capital_required = (
                        contract.strike * contract.contract_multiplier
                    )
                    max_loss = (
                        put.effective_price * contract.contract_multiplier
                    )
                    assumptions.update({
                        "contract_count": 1,
                        "cash_secured": True,
                        "premium_basis": "current_bid",
                        "option_id": contract.option_id,
                        "current_option_quote": asdict(quote),
                        "put_analysis": asdict(put),
                    })
                    option_evidence[contract.option_id] = {
                        "underlying_ticker": pack.ticker,
                        "contract": asdict(contract),
                        "current_quote": asdict(quote),
                        "put_analysis": asdict(put),
                        "premium_basis": "current_bid",
                        "contract_count": 1,
                        "marketability": marketability,
                    }
                else:
                    current_quote = pack.market.get("current_quote")
                    current_price = (
                        float(current_quote.get("close"))
                        if isinstance(current_quote, dict)
                        and isinstance(current_quote.get("close"), (int, float))
                        else None
                    )
                    if current_price is None or current_price <= 0:
                        raise ValueError(
                            f"{pack.ticker} current OPLAB price is required for covered CALL"
                        )
                    stock_quantity = float(pack.portfolio.get("stock_quantity") or 0.0)
                    covered_shares = float(contract.contract_multiplier)
                    if stock_quantity < covered_shares:
                        raise ValueError(
                            f"{normalized_option} is not covered: requires "
                            f"{covered_shares:g} shares of {pack.ticker}, "
                            f"portfolio has {stock_quantity:g}"
                        )
                    call = CallAnalysisEngine().analyze(
                        option_id=contract.option_id,
                        underlying_ticker=pack.ticker,
                        strike=contract.strike,
                        expiration_date=contract.expiration_date,
                        premium=quote.bid,
                        contract_multiplier=contract.contract_multiplier,
                        as_of=effective_as_of.date(),
                        current_price=current_price,
                    )
                    capital_required = 0.0
                    max_loss = None
                    assumptions.update({
                        "contract_count": 1,
                        "covered_call": True,
                        "premium_basis": "current_bid",
                        "option_id": contract.option_id,
                        "current_option_quote": asdict(quote),
                        "call_analysis": asdict(call),
                        "covered_shares_required": covered_shares,
                        "stock_shares_available": stock_quantity,
                    })
                    option_evidence[contract.option_id] = {
                        "underlying_ticker": pack.ticker,
                        "contract": asdict(contract),
                        "current_quote": asdict(quote),
                        "call_analysis": asdict(call),
                        "premium_basis": "current_bid",
                        "contract_count": 1,
                        "covered_shares_required": covered_shares,
                        "stock_shares_available": stock_quantity,
                        "marketability": marketability,
                    }

                alternative_sources.append(quote.source)
                all_sources.append(quote.source)

            current_quote_for_basis = pack.market.get("current_quote")
            spot_for_basis = (
                float(current_quote_for_basis.get("close"))
                if isinstance(current_quote_for_basis, dict)
                and isinstance(current_quote_for_basis.get("close"), (int, float))
                and current_quote_for_basis.get("close") > 0
                else None
            )
            stock_quantity_for_basis = float(pack.portfolio.get("stock_quantity") or 0.0)
            capital_basis: float | None = None
            if normalized_strategy == "BUY_STOCK" and amount and amount > 0:
                capital_basis = float(amount)
            elif normalized_strategy == "SELL_PUT":
                capital_basis = capital_required if capital_required and capital_required > 0 else None
            elif normalized_strategy == "SELL_CALL" and option_contract and spot_for_basis:
                capital_basis = float(option_contract.contract_multiplier) * spot_for_basis
            elif normalized_strategy in {"HOLD", "SELL_STOCK"} and stock_quantity_for_basis > 0 and spot_for_basis:
                capital_basis = stock_quantity_for_basis * spot_for_basis
            assumptions["scenario_capital_basis_brl"] = capital_basis
            assumptions["scenario_capital_basis_source"] = (
                "explicit_comparison_amount" if normalized_strategy == "BUY_STOCK"
                else "cash_secured_strike_notional" if normalized_strategy == "SELL_PUT"
                else "one_covered_contract_underlying_notional" if normalized_strategy == "SELL_CALL"
                else "known_current_stock_position_market_value" if normalized_strategy in {"HOLD", "SELL_STOCK"}
                else "UNKNOWN"
            )

            payoff_by_scenario: dict[str, float] = {}
            if shocks and horizon is not None:
                option_expiry = (
                    option_contract.expiration_date
                    if option_contract is not None
                    else None
                )
                for shock in shocks:
                    scenario_id = f"{horizon.isoformat()}:{shock:g}%"
                    if option_expiry is not None and option_expiry != horizon:
                        continue
                    current_quote = pack.market.get("current_quote")
                    current_price = (
                        float(current_quote.get("close"))
                        if isinstance(current_quote, dict)
                        and isinstance(current_quote.get("close"), (int, float))
                        and current_quote.get("close") > 0
                        else None
                    )
                    if current_price is None:
                        continue
                    terminal_price = current_price * (1 + float(shock) / 100)
                    shares = float(pack.portfolio.get("stock_quantity") or 0.0)
                    pnl: float | None = None
                    if normalized_strategy == "BUY_STOCK" and amount and amount > 0:
                        pnl = amount / current_price * (terminal_price - current_price)
                    elif normalized_strategy == "HOLD" and shares > 0:
                        pnl = shares * (terminal_price - current_price)
                    elif normalized_strategy == "SELL_STOCK" and shares > 0 and amount:
                        reduced = amount / current_price
                        pnl = max(0.0, shares - reduced) * (terminal_price - current_price)
                    elif normalized_strategy == "SELL_PUT" and option_contract and option_quote:
                        multiplier = float(option_contract.contract_multiplier)
                        pnl = float(option_quote.bid) * multiplier - max(
                            float(option_contract.strike) - terminal_price, 0.0
                        ) * multiplier
                    elif normalized_strategy == "SELL_CALL" and option_contract and option_quote:
                        multiplier = float(option_contract.contract_multiplier)
                        pnl = multiplier * (terminal_price - current_price)
                        pnl += float(option_quote.bid) * multiplier
                        pnl -= max(terminal_price - float(option_contract.strike), 0.0) * multiplier
                    if pnl is not None and math.isfinite(pnl):
                        payoff_by_scenario[scenario_id] = round(pnl, 8)

            alternative_sources = list(dict.fromkeys(alternative_sources))
            alternatives.append(
                StrategyAlternative(
                    alternative_id=(
                        f"LIVE-{index}-{subject_id}-{normalized_strategy}-"
                        f"{effective_as_of.isoformat()}"
                    ),
                    label=label,
                    action_type=normalized_strategy,
                    subject_id=subject_id,
                    as_of=effective_as_of,
                    capital_required=capital_required,
                    max_loss=max_loss,
                    payoff_by_scenario=payoff_by_scenario,
                    assumptions=assumptions,
                    evidence_refs=tuple(
                        f"strategy_evidence:{subject_id}:{source}"
                        for source in alternative_sources
                    ),
                    source_refs=tuple(alternative_sources),
                    quality_status=pack.quality_status,
                )
            )

        comparison = self.comparison_engine.compare(
            alternatives[0],
            alternatives[1],
        )
        limitations = [
            item
            for pack in packs
            for item in pack.limitations
        ]
        if any(strategy == "SELL_STOCK" for strategy in normalized_strategies):
            limitations.append(
                "SELL_STOCK is a notional what-if using the current OPLAB price; "
                "execution quantity, taxes, fees and slippage are not inferred."
            )
        if any(
            strategy in {"SELL_PUT", "SELL_CALL"}
            for strategy in normalized_strategies
        ):
            if any(strategy == "SELL_PUT" for strategy in normalized_strategies):
                limitations.append(
                    "SELL_PUT uses one cash-secured contract and the current OPLAB bid; "
                    "no option contract or execution price is inferred."
                )
            if any(strategy == "SELL_CALL" for strategy in normalized_strategies):
                limitations.append(
                    "SELL_CALL is accepted only as one covered contract using shares "
                    "already present in the canonical portfolio and the current OPLAB bid."
                )
                limitations.append(
                    "Covered CALL fair value/upside-surrender valuation remains UNKNOWN "
                    "without an explicit versioned stock valuation."
                )
            limitations.append(
                "Option marketability facts are reported directly from OPLAB; "
                "liquidity is not scored until a versioned liquidity policy is defined."
            )
        limitations.extend([
            "Expected return is not inferred from historical returns.",
            "Valuation is not computed without explicit, versioned assumptions.",
        ])
        scenario_analysis = {
            "policy_version": "terminal-price-scenarios-v1",
            "as_of": effective_as_of.isoformat(),
            "status": "NOT_REQUESTED",
            "horizon": horizon.isoformat() if horizon else None,
            "user_supplied_shocks_pct": list(shocks),
            "probabilities": None,
            "ranking": "NOT_APPLIED",
            "objective_policy": {
                "policy_version": "scenario-objective-v1",
                "requested_objective": normalized_objective,
                "status": "NOT_REQUESTED" if normalized_objective == "COMPARE_ONLY" else "UNAVAILABLE",
                "metric": "MAXIMIZE_MINIMUM_USER_SCENARIO_RETURN_ON_CAPITAL",
                "ranked_alternative_id": None,
                "tie_alternative_ids": [],
                "not_a_forecast": True,
            },
            "basis": "deterministic_expiry_payoff_vs_decision_time_reference",
            "limitations": [
                "Price shocks are user scenarios, not forecasts or probabilities.",
                "Payoff excludes taxes, fees, slippage, financing and early assignment.",
                "A position without known current shares or comparison capital remains unavailable.",
                "Option scenarios are computed only when the common horizon equals contract expiry.",
            ],
            "alternatives": [],
        }
        if shocks:
            scenario_alternatives = comparison.alternatives
            scenario_analysis["status"] = (
                "COMPUTED" if any(item.payoff_by_scenario for item in scenario_alternatives)
                else "UNAVAILABLE"
            )
            scenario_analysis["alternatives"] = [
                {
                    "alternative_id": item.alternative_id,
                    "label": item.label,
                    "underlying_ticker": (
                        (as_object := item.assumptions.get("current_underlying_quote"))
                        and as_object.get("ticker")
                    ),
                    "pnl_basis": {
                        "BUY_STOCK": "incremental P&L on the modeled purchase amount versus retaining that cash",
                        "HOLD": "change in known shares' market value versus the decision-time mark",
                        "SELL_STOCK": "change in retained shares; released sale proceeds are treated as zero-return cash",
                        "SELL_PUT": "current bid premium less terminal intrinsic loss for one contract",
                        "SELL_CALL": "covered-share price change plus current bid less terminal intrinsic call value",
                    }.get(item.action_type),
                    "capital_basis_brl": _scenario_capital_basis(item),
                    "capital_basis_source": item.assumptions.get("scenario_capital_basis_source", "UNKNOWN"),
                    "pnl_by_scenario_brl": item.payoff_by_scenario,
                    "return_by_scenario_pct": {
                        scenario_id: round(value / _scenario_capital_basis(item) * 100, 8)
                        for scenario_id, value in item.payoff_by_scenario.items()
                        if _scenario_capital_basis(item) is not None
                        and _scenario_capital_basis(item) > 0
                    },
                    "terminal_underlying_price_by_scenario": {
                        f"{horizon.isoformat()}:{shock:g}%": round(
                            float(as_object["close"]) * (1 + float(shock) / 100), 8
                        )
                        for shock in shocks
                        if horizon is not None
                        and isinstance(as_object, dict)
                        and isinstance(as_object.get("close"), (int, float))
                    },
                }
                for item in scenario_alternatives
            ]
            if any(not item.payoff_by_scenario for item in scenario_alternatives):
                scenario_analysis["status"] = "PARTIAL"
            if normalized_objective != "COMPARE_ONLY":
                expected_scenarios = {
                    f"{horizon.isoformat()}:{shock:g}%" for shock in shocks
                }
                complete = all(
                    set(item.payoff_by_scenario) == expected_scenarios
                    and (_scenario_capital_basis(item) or 0) > 0
                    for item in scenario_alternatives
                )
                objective_policy = scenario_analysis["objective_policy"]
                if complete:
                    worst_returns = [
                        min(
                            item.payoff_by_scenario[scenario_id]
                            / float(_scenario_capital_basis(item))
                            for scenario_id in expected_scenarios
                        )
                        for item in scenario_alternatives
                    ]
                    difference = worst_returns[1] - worst_returns[0]
                    objective_policy["status"] = "CONDITIONAL_RANKING" if abs(difference) > 1e-9 else "TIE"
                    if abs(difference) > 1e-9:
                        winner_index = 1 if difference > 0 else 0
                        objective_policy["ranked_alternative_id"] = scenario_alternatives[winner_index].alternative_id
                    else:
                        objective_policy["tie_alternative_ids"] = [item.alternative_id for item in scenario_alternatives]
                    objective_policy["worst_case_return_pct_by_alternative"] = {
                        item.alternative_id: round(worst * 100, 8)
                        for item, worst in zip(scenario_alternatives, worst_returns, strict=True)
                    }
                else:
                    objective_policy["reason"] = (
                        "A complete P&L for every supplied scenario and a known positive capital basis are required for both alternatives."
                    )
                scenario_analysis["ranking"] = objective_policy["status"]
            limitations.append(
                "Scenario outcomes use explicit user price shocks at the stated horizon; "
                "they are deterministic what-ifs, not expected returns or assignment probabilities."
            )
            if normalized_objective != "COMPARE_ONLY":
                limitations.append(
                    "Conditional ranking maximizes the minimum return only across the user-supplied scenarios and stated capital bases; it is not a forecast or universal recommendation."
                )
        else:
            if normalized_objective != "COMPARE_ONLY":
                scenario_analysis["status"] = "UNAVAILABLE"
            scenario_analysis["objective_policy"]["status"] = (
                "UNAVAILABLE" if normalized_objective != "COMPARE_ONLY" else "NOT_REQUESTED"
            )
            if normalized_objective != "COMPARE_ONLY":
                scenario_analysis["objective_policy"]["reason"] = "A future horizon and at least one explicit price shock are required."
        if normalized_objective == "COMPARE_ONLY":
            limitations.append("Deterministic ranking was not requested; alternatives remain unranked.")
        limitations = list(dict.fromkeys(limitations))

        put_pair = None
        if is_put_pair:
            from b3_agent.put_pair import put_pair_payload
            put_pair = put_pair_payload(comparison.alternatives,option_evidence,packs,effective_as_of,put_objective)

        if normalized_strategies == ("BUY_STOCK", "BUY_STOCK"):
            from b3_agent.price_target_evidence import StoredPriceTargetService
            target_service = StoredPriceTargetService()
            target_evidence = {ticker: target_service.build(ticker, effective_as_of) for ticker in dict.fromkeys(assets)}

        stock_purchase = None
        if normalized_strategies == ("BUY_STOCK", "BUY_STOCK"):
            from b3_agent.stock_purchase import stock_purchase_payload
            stock_purchase = stock_purchase_payload(comparison.alternatives, packs, effective_as_of, dividend_evidence, target_evidence)

        economic = None
        if stock_purchase:
            from b3_agent.economic_decision import economic_decision
            economic = economic_decision(stock_purchase, economic_inputs, effective_as_of)

        return {
            "as_of": effective_as_of,
            "quality_status": comparison.quality_status,
            "summary": (
                f"Comparação determinística construída para "
                f"{alternatives[0].label} versus {alternatives[1].label} "
                "com cotações atuais OPLAB separadas do histórico, indicadores "
                "quantitativos, fundamentos disponíveis e contexto de carteira."
                + (
                    " Política condicional aplicada aos cenários informados."
                    if scenario_analysis["ranking"] == "CONDITIONAL_RANKING"
                    else " Ranking não aplicado."
                )
            ),
            "strategy_comparison": asdict(comparison),
            "scenario_analysis": scenario_analysis,
            "asset_evidence": {
                pack.ticker: asdict(pack)
                for pack in packs
            },
            **({'put_pair_comparison':put_pair} if put_pair else {}),
            **({'stock_purchase_comparison': stock_purchase} if stock_purchase else {}),
            **({'economic_decision': economic} if economic else {}),
            "option_evidence": option_evidence,
            "limitations": limitations,
            "source_refs": list(dict.fromkeys(all_sources)),
        }


__all__ = [
    "AssetEvidencePack",
    "LiveStrategyComparisonService",
    "StrategyEvidenceService",
]


def _scenario_capital_basis(alternative: StrategyAlternative) -> float | None:
    """Return the explicit capital denominator used only for scenario ranking."""
    value = alternative.assumptions.get("scenario_capital_basis_brl")
    return float(value) if isinstance(value, (int, float)) and value > 0 else None


def _normalize_exercise_style(value: str) -> str | None:
    normalized = " ".join(value.casefold().replace("_", " ").split())
    if normalized in {"european", "europeia", "europeu", "european style"}:
        return "EUROPEAN"
    if normalized in {"american", "americana", "americano", "american style"}:
        return "AMERICAN"
    return None


def _put_model_probabilities(
    *, spot: float | None, strike: float, volatility: float | None, days: int
) -> dict[str, Any]:
    unavailable = {"expiry_itm_probability": None, "touch_probability": None}
    if spot is None or spot <= 0:
        return {**unavailable, "status": "UNKNOWN", "reason": "A current underlying price is unavailable."}
    if volatility is None or not math.isfinite(float(volatility)) or not 0 < float(volatility) <= 3:
        return {**unavailable, "status": "UNKNOWN", "reason": "A positive implied volatility in decimal units is unavailable or ambiguous."}
    if days <= 0:
        return {**unavailable, "status": "UNKNOWN", "reason": "A future expiry is required."}
    sigma = float(volatility)
    years = days / 365.0
    scale = sigma * math.sqrt(years)
    d2 = (math.log(spot / strike) - 0.5 * sigma * sigma * years) / scale
    expiry_itm = NormalDist().cdf(-d2)
    if spot <= strike:
        touch = 1.0
    else:
        distance = math.log(spot / strike)
        drift = -0.5 * sigma * sigma
        root = sigma * math.sqrt(years)
        first = NormalDist().cdf((-distance - drift * years) / root)
        second = math.exp(-2 * drift * distance / (sigma * sigma)) * NormalDist().cdf(
            (-distance + drift * years) / root
        )
        touch = min(1.0, max(0.0, first + second))
    return {
        "expiry_itm_probability": round(min(1.0, max(0.0, expiry_itm)), 8),
        "touch_probability": round(touch, 8),
        "status": "MODEL_ESTIMATE",
        "reason": None,
        "assumptions": {
            "volatility": sigma,
            "volatility_unit": "decimal annualized",
            "annual_rate": 0.0,
            "dividend_yield": 0.0,
            "days_to_expiration": days,
        },
    }
