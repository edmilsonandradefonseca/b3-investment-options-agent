from __future__ import annotations

from b3_agent.options.analysis import OptionsAnalysis
from b3_agent.schemas.opportunity import Opportunity


class OptionsOpportunityProducer:
    """Maps validated deterministic options analysis into Phase 7 opportunities.

    This producer does not invent candidates, fetch market data, or make portfolio
    decisions. It only converts already-computed PUT/CALL analytics into the
    canonical Opportunity contract.
    """

    def produce(
        self,
        analysis: OptionsAnalysis,
        *,
        as_of=None,
        source_refs: tuple[str, ...] = (),
    ) -> tuple[Opportunity, ...]:
        opportunities: list[Opportunity] = []
        effective_as_of = as_of

        for put in analysis.puts:
            if effective_as_of is None:
                raise ValueError("as_of is required when producing opportunities")
            evidence_id = f"options:{put.option_id}"
            opportunities.append(
                Opportunity(
                    opportunity_id=f"SELL_PUT:{put.option_id}",
                    ticker=put.underlying_ticker,
                    instrument_type="OPTION",
                    action="SELL_PUT",
                    as_of=effective_as_of,
                    expected_return=put.annualized_return,
                    options_analysis_ref=put.option_id,
                    capital_requirement=put.strike * put.contract_multiplier,
                    evidence_refs=(evidence_id,),
                    source_refs=source_refs or analysis.source_refs,
                    quality_status=analysis.quality_status,
                    rationale=(
                        f"Deterministic PUT analysis: effective price={put.effective_price:.6f}; "
                        f"annualized return={put.annualized_return:.6f}."
                    ),
                )
            )

        for call in analysis.calls:
            if call.action != "SELL_CALL":
                continue
            if effective_as_of is None:
                raise ValueError("as_of is required when producing opportunities")
            evidence_id = f"options:{call.option_id}"
            opportunities.append(
                Opportunity(
                    opportunity_id=f"SELL_CALL:{call.option_id}",
                    ticker=call.underlying_ticker,
                    instrument_type="OPTION",
                    action="SELL_CALL",
                    as_of=effective_as_of,
                    expected_return=call.annualized_premium_return,
                    options_analysis_ref=call.option_id,
                    capital_requirement=call.current_price * call.contract_multiplier,
                    evidence_refs=(evidence_id,),
                    source_refs=source_refs or analysis.source_refs,
                    quality_status=analysis.quality_status,
                    rationale=(
                        f"Deterministic covered CALL analysis: premium return="
                        f"{call.premium_return:.6f}; annualized premium return="
                        f"{call.annualized_premium_return:.6f}."
                    ),
                )
            )

        return tuple(opportunities)
