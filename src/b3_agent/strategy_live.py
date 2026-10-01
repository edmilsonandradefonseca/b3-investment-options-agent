from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
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
        normalized = ticker.upper().strip()
        if not normalized:
            raise ValueError("ticker must not be empty")
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
        portfolio: PortfolioContext | None = None,
        as_of: datetime | None = None,
    ) -> dict[str, Any]:
        if len(assets) != 2 or len(strategies) != 2 or len(option_ids) != 2:
            raise ValueError(
                "strategy comparison requires exactly two alternatives"
            )
        if amount is not None and amount < 0:
            raise ValueError("comparison amount must be non-negative")

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

        packs = tuple(
            self.evidence_service.build(
                ticker,
                as_of=effective_as_of,
                portfolio=portfolio,
            )
            for ticker in assets
        )

        alternatives: list[StrategyAlternative] = []
        option_evidence: dict[str, dict[str, Any]] = {}
        option_snapshots: dict[str, tuple[list[Any], list[Any]]] = {}
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
            "Deterministic comparative ranking is not yet applied.",
        ])
        limitations = list(dict.fromkeys(limitations))

        return {
            "as_of": effective_as_of,
            "quality_status": comparison.quality_status,
            "summary": (
                f"Comparação determinística construída para "
                f"{alternatives[0].label} versus {alternatives[1].label} "
                "com cotações atuais OPLAB separadas do histórico, indicadores "
                "quantitativos, fundamentos disponíveis e contexto de carteira. "
                "Ranking não aplicado."
            ),
            "strategy_comparison": asdict(comparison),
            "asset_evidence": {
                pack.ticker: asdict(pack)
                for pack in packs
            },
            "option_evidence": option_evidence,
            "limitations": limitations,
            "source_refs": list(dict.fromkeys(all_sources)),
        }


__all__ = [
    "AssetEvidencePack",
    "LiveStrategyComparisonService",
    "StrategyEvidenceService",
]
