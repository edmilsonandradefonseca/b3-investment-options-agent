from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol

from b3_agent.orchestration.live_providers import LiveProviderService
from b3_agent.portfolio.snapshot import load_active_snapshots
from b3_agent.providers.brapi.fundamentals import BrapiFundamentalsAdapter
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
        history_days: int = 120,
    ) -> None:
        if history_days < 1:
            raise ValueError("history_days must be positive")
        self.market_provider = market_provider or LiveProviderService().market_provider
        self.fundamentals_provider = (
            fundamentals_provider or BrapiFundamentalsAdapter()
        )
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
                "history_count": len(market_records),
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
    """Compose UC-04 BUY_STOCK/HOLD alternatives from live deterministic facts.

    This is an additive V4.3 composition service. It deliberately does not rank
    alternatives and does not manufacture expected returns or valuation inputs.
    """

    _STRATEGY_ALIASES = {
        "comprar ação": "BUY_STOCK",
        "comprar acao": "BUY_STOCK",
        "buy stock": "BUY_STOCK",
        "buy_stock": "BUY_STOCK",
        "manter": "HOLD",
        "hold": "HOLD",
    }

    def __init__(
        self,
        *,
        evidence_service: StrategyEvidenceService | None = None,
        comparison_engine: StrategyComparisonEngine | None = None,
    ) -> None:
        self.evidence_service = evidence_service or StrategyEvidenceService()
        self.comparison_engine = comparison_engine or StrategyComparisonEngine()

    @classmethod
    def normalize_strategy(cls, value: str) -> str | None:
        return cls._STRATEGY_ALIASES.get(" ".join(value.casefold().split()))

    @classmethod
    def supports(cls, values: tuple[str, str]) -> bool:
        return all(cls.normalize_strategy(value) is not None for value in values)

    def compare(
        self,
        *,
        assets: tuple[str, str],
        strategies: tuple[str, str],
        amount: float | None = None,
        portfolio: PortfolioContext | None = None,
        as_of: datetime | None = None,
    ) -> dict[str, Any]:
        if len(assets) != 2 or len(strategies) != 2:
            raise ValueError("strategy comparison requires exactly two alternatives")
        if amount is not None and amount < 0:
            raise ValueError("comparison amount must be non-negative")

        normalized_strategies = tuple(
            self.normalize_strategy(value) for value in strategies
        )
        if any(value is None for value in normalized_strategies):
            raise ValueError(
                "live deterministic comparison currently supports BUY_STOCK and HOLD"
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

        alternatives = []
        for index, (pack, original, normalized_strategy) in enumerate(
            zip(packs, strategies, normalized_strategies, strict=True),
            start=1,
        ):
            assert normalized_strategy is not None
            alternatives.append(
                StrategyAlternative(
                    alternative_id=(
                        f"LIVE-{index}-{pack.ticker}-{normalized_strategy}-"
                        f"{effective_as_of.isoformat()}"
                    ),
                    label=f"{original} · {pack.ticker}",
                    action_type=normalized_strategy,
                    subject_id=pack.ticker,
                    as_of=effective_as_of,
                    capital_required=(
                        amount if normalized_strategy == "BUY_STOCK" else 0.0
                    ),
                    assumptions={
                        "amount": amount,
                        "expected_return": "not_inferred",
                        "valuation": "not_computed_without_explicit_assumptions",
                        "ranking": "not_applied",
                    },
                    evidence_refs=tuple(
                        f"asset_evidence:{pack.ticker}:{source}"
                        for source in pack.source_refs
                    ),
                    source_refs=pack.source_refs,
                    quality_status=pack.quality_status,
                )
            )

        comparison = self.comparison_engine.compare(
            alternatives[0],
            alternatives[1],
        )
        limitations = tuple(
            dict.fromkeys(
                [
                    *(
                        item
                        for pack in packs
                        for item in pack.limitations
                    ),
                    "Expected return is not inferred from historical returns.",
                    "Valuation is not computed without explicit, versioned assumptions.",
                    "Deterministic comparative ranking is not yet applied.",
                ]
            )
        )
        quality = comparison.quality_status

        return {
            "as_of": effective_as_of,
            "quality_status": quality,
            "summary": (
                f"Comparação determinística construída para "
                f"{alternatives[0].label} versus {alternatives[1].label} "
                "com dados de mercado, indicadores quantitativos, fundamentos "
                "disponíveis e contexto de carteira. Ranking não aplicado."
            ),
            "strategy_comparison": asdict(comparison),
            "asset_evidence": {
                pack.ticker: asdict(pack)
                for pack in packs
            },
            "limitations": list(limitations),
            "source_refs": list(
                dict.fromkeys(
                    source
                    for pack in packs
                    for source in pack.source_refs
                )
            ),
        }


__all__ = [
    "AssetEvidencePack",
    "LiveStrategyComparisonService",
    "StrategyEvidenceService",
]
