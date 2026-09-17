from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping, Sequence

from .call import CallAnalysisEngine, CallOpportunity
from .put import PutAnalysisEngine, PutOpportunity
from b3_agent.schemas.option import OptionContract, OptionQuote


@dataclass(frozen=True)
class OptionsAnalysis:
    """Unified deterministic result for PUT and covered CALL analysis."""

    puts: tuple[PutOpportunity, ...] = ()
    calls: tuple[CallOpportunity, ...] = ()
    source_refs: tuple[str, ...] = ()
    quality_status: str = "VALIDATED"
    assumptions: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.quality_status not in {"VALIDATED", "WARNING", "REJECTED"}:
            raise ValueError("invalid quality_status")

    @property
    def opportunities(self) -> tuple[PutOpportunity | CallOpportunity, ...]:
        return self.puts + self.calls


class OptionsAnalysisEngine:
    """Deterministic composition layer for validated option contracts and quotes."""

    def analyze_quotes(
        self,
        *,
        contracts: Sequence[OptionContract],
        quotes: Sequence[OptionQuote],
        as_of: date,
        current_prices: Mapping[str, float] | None = None,
        fair_values: Mapping[str, float] | None = None,
        source_refs: tuple[str, ...] = (),
        quality_status: str = "VALIDATED",
        assumptions: dict[str, Any] | None = None,
        call_min_annualized_premium_return: float = 0.0,
        call_min_total_return_if_assigned: float = 0.0,
        call_max_upside_surrendered: float | None = None,
    ) -> OptionsAnalysis:
        """Analyze validated quotes using the canonical PUT/CALL engines.

        Quote premium selection is deterministic: mid, then last, then the
        midpoint of bid/ask. Missing pricing data rejects that individual
        contract instead of inventing a value.
        """
        contracts_by_id = {contract.option_id: contract for contract in contracts}
        current_prices = current_prices or {}
        fair_values = fair_values or {}
        puts: list[PutOpportunity] = []
        calls: list[CallOpportunity] = []
        assumptions_out = dict(assumptions or {})
        rejected: list[str] = []

        for quote in quotes:
            contract = contracts_by_id.get(quote.option_id)
            if contract is None:
                rejected.append(f"missing_contract:{quote.option_id}")
                continue
            premium = self._premium_from_quote(quote)
            if premium is None:
                rejected.append(f"missing_premium:{quote.option_id}")
                continue

            option_type = contract.option_type.strip().upper()
            fair_value = fair_values.get(contract.option_id)
            common = dict(
                option_id=contract.option_id,
                underlying_ticker=contract.underlying_ticker,
                strike=contract.strike,
                expiration_date=contract.expiration_date,
                premium=premium,
                contract_multiplier=contract.contract_multiplier,
                as_of=as_of,
                fair_value=fair_value,
            )

            if option_type in {"P", "PUT"}:
                puts.append(PutAnalysisEngine().analyze(**common))
            elif option_type in {"C", "CALL"}:
                current_price = current_prices.get(contract.underlying_ticker)
                if current_price is None:
                    rejected.append(f"missing_current_price:{quote.option_id}")
                    continue
                calls.append(
                    CallAnalysisEngine().analyze(
                        **common,
                        current_price=current_price,
                        min_annualized_premium_return=call_min_annualized_premium_return,
                        min_total_return_if_assigned=call_min_total_return_if_assigned,
                        max_upside_surrendered=call_max_upside_surrendered,
                    )
                )
            else:
                rejected.append(f"unsupported_option_type:{quote.option_id}")

        if rejected:
            assumptions_out["rejected_quotes"] = tuple(rejected)
            if quality_status == "VALIDATED":
                quality_status = "WARNING"

        return self.combine(
            puts=tuple(puts),
            calls=tuple(calls),
            source_refs=source_refs,
            quality_status=quality_status,
            assumptions=assumptions_out or None,
        )

    @staticmethod
    def _premium_from_quote(quote: OptionQuote) -> float | None:
        if quote.mid is not None and quote.mid >= 0:
            return float(quote.mid)
        if quote.last is not None and quote.last >= 0:
            return float(quote.last)
        if quote.bid is not None and quote.ask is not None:
            if quote.bid >= 0 and quote.ask >= 0:
                return float((quote.bid + quote.ask) / 2.0)
        return None

    def combine(
        self,
        *,
        puts: tuple[PutOpportunity, ...] = (),
        calls: tuple[CallOpportunity, ...] = (),
        source_refs: tuple[str, ...] = (),
        quality_status: str = "VALIDATED",
        assumptions: dict[str, Any] | None = None,
    ) -> OptionsAnalysis:
        return OptionsAnalysis(
            puts=puts,
            calls=calls,
            source_refs=source_refs,
            quality_status=quality_status,
            assumptions=assumptions,
        )
