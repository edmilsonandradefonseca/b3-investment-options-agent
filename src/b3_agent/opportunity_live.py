from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from b3_agent.opportunity_pipeline import OpportunityPipeline
from b3_agent.options.analysis import OptionsAnalysis
from b3_agent.options.put import PutAnalysisEngine
from b3_agent.orchestration.live_providers import LiveProviderService
from b3_agent.schemas.opportunity import OpportunitySet


MARKETABILITY_POLICY = "B3_OPTION_MARKETABILITY_V1"


@dataclass(frozen=True)
class LiveOpportunityResult:
    ticker: str
    as_of: datetime
    opportunity_set: OpportunitySet
    option_marketability: dict[str, dict[str, Any]]
    limitations: tuple[str, ...]


class LiveOpportunityService:
    """Build a bounded canonical UC-03 set from executable live option facts.

    This service deliberately does not fabricate a stock valuation. Until a
    versioned stock valuation is available, live stock evidence is interpreted
    by the agents but cannot become a ranked BUY/ACCUMULATE opportunity.

    SELL_PUT candidates are deterministic and use the current OPLAB *bid* as the
    executable premium basis. The marketability policy is intentionally simple
    and auditable: a non-expired PUT must have a current two-sided market
    (bid > 0 and ask > 0). Volume, open interest and spread remain reported facts;
    no liquidity threshold, liquidity score or LLM judgment is introduced.
    """

    def __init__(
        self,
        *,
        live_provider: LiveProviderService | None = None,
        pipeline: OpportunityPipeline | None = None,
    ) -> None:
        self.live_provider = live_provider or LiveProviderService()
        self.pipeline = pipeline or OpportunityPipeline()

    def build(
        self,
        ticker: str,
        *,
        as_of: datetime | None = None,
        limit: int = 20,
    ) -> LiveOpportunityResult:
        if limit < 1:
            raise ValueError("limit must be positive")
        effective_as_of = as_of or datetime.now(timezone.utc)
        if effective_as_of.tzinfo is None or effective_as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")

        snapshot = self.live_provider.load(ticker, as_of=effective_as_of)
        contracts = {item.option_id: item for item in snapshot.option_contracts}
        quotes = {item.option_id: item for item in snapshot.option_quotes}

        puts = []
        marketability: dict[str, dict[str, Any]] = {}
        for option_id, contract in contracts.items():
            if contract.option_type.upper() != "PUT":
                continue
            if contract.expiration_date <= effective_as_of.date():
                continue
            quote = quotes.get(option_id)
            if quote is None:
                continue

            bid = quote.bid
            ask = quote.ask
            volume = quote.volume
            eligible = (
                bid is not None
                and bid > 0
                and ask is not None
                and ask > 0
            )
            spread_abs = (
                ask - bid
                if bid is not None and ask is not None and ask >= bid
                else None
            )
            mid = (
                quote.mid
                if quote.mid is not None and quote.mid > 0
                else ((bid + ask) / 2.0 if bid and ask else None)
            )
            spread_pct_of_mid = (
                spread_abs / mid
                if spread_abs is not None and mid is not None and mid > 0
                else None
            )
            marketability[option_id] = {
                "policy_version": MARKETABILITY_POLICY,
                "eligible": eligible,
                "bid": bid,
                "ask": ask,
                "last": quote.last,
                "mid": mid,
                "volume": volume,
                "open_interest": quote.open_interest,
                "spread_abs": spread_abs,
                "spread_pct_of_mid": spread_pct_of_mid,
                "source": quote.source,
                "as_of": quote.observation_timestamp,
            }
            if not eligible:
                continue

            puts.append(
                PutAnalysisEngine().analyze(
                    option_id=contract.option_id,
                    underlying_ticker=contract.underlying_ticker,
                    strike=contract.strike,
                    expiration_date=contract.expiration_date,
                    premium=float(bid),
                    contract_multiplier=contract.contract_multiplier,
                    as_of=effective_as_of.date(),
                )
            )

        analysis = OptionsAnalysis(
            puts=tuple(puts),
            calls=(),
            source_refs=snapshot.source_refs,
            quality_status="WARNING",
            assumptions={
                "premium_basis": "current_bid",
                "marketability_policy": MARKETABILITY_POLICY,
                "stock_opportunities": "not_built_without_versioned_valuation",
            },
        )
        built = self.pipeline.build_from_inputs(
            as_of=effective_as_of,
            options_analyses=(analysis,),
            source_refs=snapshot.source_refs,
        )

        ranked = tuple(built.ranked_opportunities[:limit])
        selected_ids = {item.opportunity_id for item in ranked}
        action_candidates = tuple(
            item
            for item in built.action_candidates
            if any(ref in selected_ids for ref in item.opportunity_refs)
        )
        bounded = OpportunitySet(
            as_of=built.as_of,
            ranked_opportunities=ranked,
            rejected_opportunities=built.rejected_opportunities,
            action_candidates=action_candidates,
            relative_opportunities=built.relative_opportunities,
            signals=built.signals,
            threats=built.threats,
            events=built.events,
            impacts=built.impacts,
            ranking_policy_version=(
                f"{built.ranking_policy_version}+{MARKETABILITY_POLICY}"
            ),
            source_refs=built.source_refs,
            quality_status="WARNING",
        )

        limitations = [
            "Stock BUY/ACCUMULATE opportunities are not ranked without a "
            "versioned deterministic stock valuation.",
            "SELL_PUT candidates use current OPLAB bid as executable premium.",
            "Marketability requires a positive two-sided bid/ask market; "
            "volume, open interest and spread are reported but not used as "
            "unversioned liquidity thresholds.",
        ]
        if not ranked:
            limitations.append(
                "No SELL_PUT candidate satisfied the current marketability policy."
            )

        selected_option_ids = {
            item.options_analysis_ref
            for item in ranked
            if item.options_analysis_ref
        }
        bounded_marketability = {
            option_id: details
            for option_id, details in marketability.items()
            if option_id in selected_option_ids
        }

        return LiveOpportunityResult(
            ticker=snapshot.ticker,
            as_of=effective_as_of,
            opportunity_set=bounded,
            option_marketability=bounded_marketability,
            limitations=tuple(limitations),
        )

    @staticmethod
    def as_payload(result: LiveOpportunityResult) -> dict[str, Any]:
        return {
            "ticker": result.ticker,
            "as_of": result.as_of,
            "opportunity_set": asdict(result.opportunity_set),
            "option_marketability": result.option_marketability,
            "limitations": list(result.limitations),
        }


__all__ = [
    "LiveOpportunityResult",
    "LiveOpportunityService",
    "MARKETABILITY_POLICY",
]
