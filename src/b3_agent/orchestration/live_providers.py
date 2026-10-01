from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from b3_agent.config import settings
from b3_agent.options.analysis import OptionsAnalysis, OptionsAnalysisEngine
from b3_agent.providers.brapi.adapter import BrapiAdapter
from b3_agent.providers.brapi.cache import CachedBrapiAdapter
from b3_agent.providers.local_market_history import LocalFirstMarketDataAdapter
from b3_agent.providers.oplab.adapter import OplabAdapter
from b3_agent.providers.oplab.historical import OplabHistoricalAdapter
from b3_agent.providers.oplab.options import OplabOptionsAdapter
from b3_agent.schemas.market import StockMarketData
from b3_agent.schemas.option import OptionContract, OptionQuote


@dataclass(frozen=True)
class LiveProviderSnapshot:
    ticker: str
    as_of: datetime
    market_records: tuple[StockMarketData, ...]
    current_stock_quote: StockMarketData | None
    option_contracts: tuple[OptionContract, ...]
    option_quotes: tuple[OptionQuote, ...]
    options_analysis: OptionsAnalysis
    source_refs: tuple[str, ...]


class LiveProviderService:
    """Acquire current provider data and normalize it for deterministic engines.

    Daily-market precedence is COTAHIST -> OPLAB -> cached BRAPI. OPLAB also
    supplies the current option chain. The service performs no investment
    recommendation or LLM reasoning.
    """

    def __init__(
        self,
        *,
        market_provider: (
            BrapiAdapter
            | CachedBrapiAdapter
            | LocalFirstMarketDataAdapter
            | OplabHistoricalAdapter
            | None
        ) = None,
        options_provider: OplabOptionsAdapter | None = None,
        current_market_provider: OplabAdapter | None = None,
        history_days: int = 120,
    ) -> None:
        if history_days < 1:
            raise ValueError("history_days must be positive")
        self.market_provider = market_provider or LocalFirstMarketDataAdapter(
            settings.data_dir / "archive" / "cotahist_raw",
            settings.data_dir / "cache" / "brapi_daily",
            oplab_provider=OplabHistoricalAdapter(),
        )
        self.options_provider = options_provider or OplabOptionsAdapter()
        self.current_market_provider = current_market_provider or OplabAdapter()
        self.history_days = history_days

    def load(self, ticker: str, *, as_of: datetime | None = None) -> LiveProviderSnapshot:
        normalized = ticker.upper().strip()
        if not normalized:
            raise ValueError("ticker must not be empty")
        effective_as_of = as_of or datetime.now(timezone.utc)
        if effective_as_of.tzinfo is None or effective_as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")

        end = effective_as_of.date()
        start = end - timedelta(days=self.history_days)
        market_records = tuple(
            self.market_provider.get_market_data(normalized, start, end)
        )
        if not market_records:
            raise ValueError(f"no market data returned for {normalized}")

        current_stock_quote = None
        current_quote_error = None
        try:
            current_stock_quote = self.current_market_provider.get_current_quote(
                normalized
            )
        except (OSError, RuntimeError, ValueError) as exc:
            current_quote_error = str(exc)

        if isinstance(self.options_provider, OplabOptionsAdapter):
            option_contracts, option_quotes = self.options_provider.get_snapshot(
                normalized, effective_as_of
            )
        else:
            option_contracts = self.options_provider.get_options(
                normalized, effective_as_of
            )
            option_quotes = self.options_provider.get_option_quotes(
                normalized, effective_as_of
            )
        contracts = tuple(option_contracts)
        quotes = tuple(option_quotes)

        latest = max(
            market_records,
            key=lambda item: item.observation_timestamp,
        )
        market_sources = tuple(
            dict.fromkeys(record.source for record in market_records)
        )
        quote_sources = (
            (current_stock_quote.source,)
            if current_stock_quote is not None
            else ()
        )
        source_refs = tuple(
            dict.fromkeys(
                (*market_sources, *quote_sources, self.options_provider.name)
            )
        )
        current_prices = (
            {normalized: current_stock_quote.close}
            if current_stock_quote is not None
            else {}
        )
        assumptions = {
            "live_provider_snapshot": True,
            "market_history_start": start.isoformat(),
            "market_history_end": end.isoformat(),
            "market_provider_precedence": "COTAHIST>OPLAB>BRAPI",
            "current_stock_price_source": (
                current_stock_quote.source
                if current_stock_quote is not None
                else "unavailable"
            ),
        }
        if current_quote_error is not None:
            assumptions["current_stock_quote_error"] = current_quote_error
        analysis = OptionsAnalysisEngine().analyze_quotes(
            contracts=contracts,
            quotes=quotes,
            as_of=end,
            current_prices=current_prices,
            source_refs=source_refs,
            assumptions=assumptions,
        )

        return LiveProviderSnapshot(
            ticker=normalized,
            as_of=effective_as_of,
            market_records=market_records,
            current_stock_quote=current_stock_quote,
            option_contracts=contracts,
            option_quotes=quotes,
            options_analysis=analysis,
            source_refs=source_refs,
        )
