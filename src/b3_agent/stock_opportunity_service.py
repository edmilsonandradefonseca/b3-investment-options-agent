from __future__ import annotations

from datetime import date, datetime, time

from b3_agent.opportunity_stock import StockOpportunityProducer
from b3_agent.quant_engine import compute_quant_features
from b3_agent.schemas.market import StockMarketData
from b3_agent.schemas.opportunity import Opportunity
from b3_agent.schemas.valuation import ValuationRange


AS_OF = date | datetime


class StockOpportunityService:
    """Integrate point-in-time stock market data with deterministic valuation.

    This service does not fetch external data, calculate valuation, rank
    opportunities, or make portfolio decisions.
    """

    def __init__(self, *, producer: StockOpportunityProducer | None = None) -> None:
        self._producer = producer or StockOpportunityProducer()

    def produce(
        self,
        records: list[StockMarketData],
        valuation: ValuationRange,
        *,
        as_of: AS_OF | None = None,
        benchmark_records: list[StockMarketData] | None = None,
        source_refs: tuple[str, ...] = (),
    ) -> tuple[Opportunity, ...]:
        if not records:
            raise ValueError("records must not be empty")

        effective_as_of = as_of if as_of is not None else valuation.as_of
        decision_timestamp = self._as_datetime(effective_as_of)

        eligible_records = [
            record
            for record in records
            if self._observation_is_before_or_at(
                record.observation_timestamp,
                effective_as_of,
            )
            and record.is_available_at(decision_timestamp)
        ]

        if not eligible_records:
            raise ValueError(
                "no stock market observations are available at decision timestamp"
            )

        eligible_records.sort(key=lambda record: record.observation_timestamp)
        latest = eligible_records[-1]

        if latest.close <= 0:
            raise ValueError("latest market close must be positive")

        quant_features = compute_quant_features(
            eligible_records,
            as_of=effective_as_of,
            benchmark_records=benchmark_records,
        )

        market_source_refs = tuple(
            dict.fromkeys(
                record.source
                for record in eligible_records
                if record.source
            )
        )

        return self._producer.produce(
            valuation,
            current_price=latest.close,
            quant_features=quant_features,
            as_of=effective_as_of,
            source_refs=(*market_source_refs, *source_refs),
        )

    @staticmethod
    def _as_datetime(value: AS_OF) -> datetime:
        if isinstance(value, datetime):
            return value
        return datetime.combine(value, time.max)

    @staticmethod
    def _observation_is_before_or_at(
        observation: datetime,
        as_of: AS_OF,
    ) -> bool:
        if isinstance(as_of, datetime):
            return observation <= as_of
        return observation.date() <= as_of
