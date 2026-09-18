from __future__ import annotations

from datetime import date, datetime

from b3_agent.schemas.opportunity import Opportunity
from b3_agent.schemas.quant import QuantFeatures
from b3_agent.schemas.valuation import ValuationRange


AS_OF = date | datetime


class StockOpportunityProducer:
    """Maps deterministic stock valuation into canonical opportunities.

    This producer does not fetch market data, calculate valuation, rank
    opportunities, or make portfolio decisions. It only converts an already
    validated ValuationRange plus current price into an Opportunity contract.
    """

    def produce(
        self,
        valuation: ValuationRange,
        *,
        current_price: float,
        quant_features: QuantFeatures | None = None,
        as_of: AS_OF | None = None,
        source_refs: tuple[str, ...] = (),
    ) -> tuple[Opportunity, ...]:
        if current_price <= 0:
            raise ValueError("current_price must be positive")

        if valuation.quality_status == "REJECTED":
            return ()

        effective_as_of = as_of if as_of is not None else valuation.as_of

        expected_return = (
            valuation.base_value / current_price
        ) - 1.0

        valuation_ref = (
            f"valuation:{valuation.ticker}:{valuation.method}"
        )

        quant_ref = (
            f"quant:{quant_features.ticker}:{quant_features.as_of}"
            if quant_features is not None
            else None
        )

        evidence_refs = [
            valuation_ref,
            f"price:{valuation.ticker}:{current_price}",
        ]

        if quant_ref is not None:
            evidence_refs.append(quant_ref)

        combined_sources = tuple(
            dict.fromkeys(
                (
                    *valuation.source_refs,
                    *source_refs,
                )
            )
        )

        if valuation.accumulation_price is not None:
            if current_price <= valuation.accumulation_price:
                return (
                    Opportunity(
                        opportunity_id=(
                            f"{valuation.ticker}:ACCUMULATE:{valuation.method}"
                        ),
                        ticker=valuation.ticker,
                        instrument_type="STOCK",
                        action="ACCUMULATE",
                        as_of=effective_as_of,
                        expected_return=expected_return,
                        valuation_range_ref=valuation_ref,
                        quant_features_ref=quant_ref,
                        capital_requirement=current_price,
                        liquidity_value=None,
                        evidence_refs=tuple(evidence_refs),
                        source_refs=combined_sources,
                        quality_status=valuation.quality_status,
                        rationale=(
                            "Current price is at or below the deterministic "
                            "accumulation threshold."
                        ),
                    ),
                )

        if (
            valuation.accumulation_price is not None
            and valuation.reduce_price is not None
            and valuation.accumulation_price < current_price < valuation.reduce_price
        ):
            return (
                Opportunity(
                    opportunity_id=(
                        f"{valuation.ticker}:BUY:{valuation.method}"
                    ),
                    ticker=valuation.ticker,
                    instrument_type="STOCK",
                    action="BUY",
                    as_of=effective_as_of,
                    expected_return=expected_return,
                    valuation_range_ref=valuation_ref,
                    quant_features_ref=quant_ref,
                    capital_requirement=current_price,
                    liquidity_value=None,
                    evidence_refs=tuple(evidence_refs),
                    source_refs=combined_sources,
                    quality_status=valuation.quality_status,
                    rationale=(
                        "Current price is above the accumulation threshold "
                        "and below the deterministic reduction threshold."
                    ),
                ),
            )

        return ()

