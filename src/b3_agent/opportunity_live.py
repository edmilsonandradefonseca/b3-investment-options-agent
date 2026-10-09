from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from b3_agent.config import settings
from b3_agent.opportunity_pipeline import OpportunityPipeline
from b3_agent.options.analysis import OptionsAnalysis
from b3_agent.options.call import CallAnalysisEngine
from b3_agent.options.put import PutAnalysisEngine
from b3_agent.portfolio.snapshot import load_active_snapshots
from b3_agent.orchestration.live_providers import LiveProviderService
from b3_agent.schemas.opportunity import OpportunitySet
from b3_agent.schemas.position import PortfolioContext


MARKETABILITY_POLICY = "B3_OPTION_MARKETABILITY_V1"
CANDIDATE_ORDER_POLICY = "B3_LIVE_OPTION_CANDIDATE_ORDER_V1"


@dataclass(frozen=True)
class LiveOpportunityResult:
    ticker: str
    as_of: datetime
    opportunity_set: OpportunitySet
    option_marketability: dict[str, dict[str, Any]]
    ranking_status: str
    ranking_reason: str
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
        portfolio: PortfolioContext | None = None,
    ) -> LiveOpportunityResult:
        if limit < 1:
            raise ValueError("limit must be positive")
        effective_as_of = as_of or datetime.now(timezone.utc)
        if effective_as_of.tzinfo is None or effective_as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")

        snapshot = self.live_provider.load(ticker, as_of=effective_as_of)
        contracts = {item.option_id: item for item in snapshot.option_contracts}
        quotes = {item.option_id: item for item in snapshot.option_quotes}

        if portfolio is None:
            try:
                candidate = load_active_snapshots(settings.data_dir).get(
                    "portfolio_context"
                )
                if isinstance(candidate, PortfolioContext):
                    portfolio = candidate
            except (OSError, RuntimeError, ValueError):
                portfolio = None

        normalized_ticker = snapshot.ticker.upper()
        stock_quantity = 0.0
        if portfolio is not None:
            stock_quantity = sum(
                float(position.quantity)
                for position in portfolio.positions
                if position.instrument_type.upper() != "OPTION"
                and position.ticker.upper() == normalized_ticker
                and position.quantity > 0
            )

        current_price = (
            snapshot.current_stock_quote.close
            if snapshot.current_stock_quote is not None
            else None
        )

        puts = []
        calls = []
        marketability: dict[str, dict[str, Any]] = {}
        for option_id, contract in contracts.items():
            option_type = contract.option_type.upper()
            if option_type not in {"PUT", "CALL"}:
                continue
            if contract.expiration_date <= effective_as_of.date():
                continue
            quote = quotes.get(option_id)
            if quote is None:
                continue

            bid = quote.bid
            ask = quote.ask
            volume = quote.volume
            two_sided = (
                bid is not None
                and bid > 0
                and ask is not None
                and ask > 0
            )
            covered_call = (
                option_type == "CALL"
                and stock_quantity >= float(contract.contract_multiplier)
            )
            eligible = two_sided and (
                option_type == "PUT" or covered_call
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
                "option_type": option_type,
                "candidate_action": (
                    "SELL_PUT" if option_type == "PUT" else "SELL_CALL"
                ),
                "covered_call": covered_call if option_type == "CALL" else None,
                "stock_shares_available": (
                    stock_quantity if option_type == "CALL" else None
                ),
                "covered_shares_required": (
                    float(contract.contract_multiplier)
                    if option_type == "CALL"
                    else None
                ),
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
                "strike": contract.strike,
                "expiration_date": contract.expiration_date,
                "days_to_expiration": (
                    contract.expiration_date - effective_as_of.date()
                ).days,
            }
            if not eligible:
                continue

            if option_type == "PUT":
                put_analysis = PutAnalysisEngine().analyze(
                    option_id=contract.option_id,
                    underlying_ticker=contract.underlying_ticker,
                    strike=contract.strike,
                    expiration_date=contract.expiration_date,
                    premium=float(bid),
                    contract_multiplier=contract.contract_multiplier,
                    as_of=effective_as_of.date(),
                )
                marketability[option_id].update({
                    "effective_price": put_analysis.effective_price,
                    "premium_yield": (
                        put_analysis.premium / put_analysis.effective_price
                    ),
                    "annualized_return": put_analysis.annualized_return,
                })
                puts.append(put_analysis)
            else:
                if current_price is None or current_price <= 0:
                    continue
                call_analysis = CallAnalysisEngine().analyze(
                    option_id=contract.option_id,
                    underlying_ticker=contract.underlying_ticker,
                    strike=contract.strike,
                    expiration_date=contract.expiration_date,
                    premium=float(bid),
                    contract_multiplier=contract.contract_multiplier,
                    as_of=effective_as_of.date(),
                    current_price=float(current_price),
                )
                marketability[option_id].update({
                    "premium_yield": call_analysis.premium_return,
                    "annualized_return": call_analysis.annualized_premium_return,
                    "gain_to_strike": call_analysis.gain_to_strike,
                    "total_return_if_assigned": (
                        call_analysis.total_return_if_assigned
                    ),
                    "covered_position_value": (
                        float(current_price)
                        * float(contract.contract_multiplier)
                    ),
                    "incremental_capital_required": 0.0,
                })
                calls.append(call_analysis)

        analysis = OptionsAnalysis(
            puts=tuple(puts),
            calls=tuple(calls),
            source_refs=snapshot.source_refs,
            quality_status="WARNING",
            assumptions={
                "premium_basis": "current_bid",
                "marketability_policy": MARKETABILITY_POLICY,
                "stock_opportunities": "not_built_without_versioned_valuation",
                "covered_call_requires_canonical_stock_holding": True,
                "stock_shares_available": stock_quantity,
            },
        )
        built = self.pipeline.build_from_inputs(
            as_of=effective_as_of,
            options_analyses=(analysis,),
            source_refs=snapshot.source_refs,
        )

        # UC-03 requires valuation, risk, liquidity, portfolio impact and
        # a declared objective for an economic ranking. Personal experience is optional. The live path does not yet
        # have all of those canonical dimensions, so annualized return must not
        # silently become the deciding score. Preserve a deterministic candidate
        # order by expiration/strike/id and explicitly defer economic ranking.
        def candidate_order(item):
            option_id = item.options_analysis_ref or ""
            contract = contracts.get(option_id)
            return (
                contract.expiration_date if contract is not None else effective_as_of.date(),
                contract.strike if contract is not None else float("inf"),
                item.opportunity_id,
            )

        ranked = tuple(
            sorted(
                built.ranked_opportunities,
                key=candidate_order,
            )[:limit]
        )
        ranking_status = "DEFERRED_INCOMPLETE_CONTEXT"
        ranking_reason = (
            "Economic ranking is deferred because canonical valuation, risk, "
            "portfolio impact, liquidity policy and a declared ranking objective "
            "are not all available. Annualized return remains evidence only."
        )
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
                f"{built.ranking_policy_version}+{MARKETABILITY_POLICY}+"
                f"{CANDIDATE_ORDER_POLICY}"
            ),
            source_refs=built.source_refs,
            quality_status="WARNING",
        )

        limitations = [
            "Stock BUY/ACCUMULATE opportunities are not ranked without a "
            "versioned deterministic stock valuation.",
            "SELL_PUT and covered SELL_CALL candidates use current OPLAB bid as executable premium.",
            "SELL_CALL candidates are emitted only when the canonical portfolio "
            "contains enough underlying shares for one covered contract.",
            "Marketability requires a positive two-sided bid/ask market; "
            "volume, open interest and spread are reported but not used as "
            "unversioned liquidity thresholds.",
            ranking_reason,
        ]
        if not ranked:
            limitations.append(
                "No option candidate satisfied the current marketability and "
                "portfolio-coverage policy."
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
            ranking_status=ranking_status,
            ranking_reason=ranking_reason,
            limitations=tuple(limitations),
        )

    @staticmethod
    def as_payload(result: LiveOpportunityResult) -> dict[str, Any]:
        return {
            "ticker": result.ticker,
            "as_of": result.as_of,
            "opportunity_set": asdict(result.opportunity_set),
            "option_marketability": result.option_marketability,
            "opportunity_ranking_status": result.ranking_status,
            "opportunity_ranking_reason": result.ranking_reason,
            "limitations": list(result.limitations),
        }


__all__ = [
    "LiveOpportunityResult",
    "LiveOpportunityService",
    "MARKETABILITY_POLICY",
    "CANDIDATE_ORDER_POLICY",
]
