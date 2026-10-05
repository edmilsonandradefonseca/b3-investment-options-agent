"""Yahoo adapter for B3 stocks; no option-chain or executable-price promises."""
from datetime import date, datetime, timedelta, timezone
import math
import re

from b3_agent.providers.fundamental_units import FRACTIONS, MONEY, MULTIPLES, PER_SHARE, fundamental_unit
from b3_agent.providers.http_retry import ProviderRequestError
from b3_agent.schemas.market import StockMarketData
from b3_agent.schemas.fundamental import StockFundamental
from b3_agent.schemas.dividend import DividendRecord


def yahoo_symbol(ticker: str) -> str:
    normalized = ticker.strip().upper()
    if not re.fullmatch(r"[A-Z]{4}\d{1,2}", normalized):
        raise ValueError("invalid B3 equity ticker")
    return normalized + ".SA"


def finite(value):
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None


class YahooAdapter:
    name = "yahoo"

    def __init__(self, ticker_factory=None):
        self.ticker_factory = ticker_factory

    def _ticker(self, ticker):
        symbol = yahoo_symbol(ticker)
        if self.ticker_factory is not None:
            return self.ticker_factory(symbol)
        try:
            import yfinance as yf
        except ImportError as exc:
            raise ProviderRequestError("yfinance not installed") from exc
        return yf.Ticker(symbol)

    def get_market_data(self, ticker: str, start: date, end: date) -> list[StockMarketData]:
        if start > end:
            raise ValueError("invalid date range")
        instrument = self._ticker(ticker)
        try:
            frame = instrument.history(start=start.isoformat(), end=(end+timedelta(days=1)).isoformat(),
                interval="1d", auto_adjust=False, back_adjust=False, repair=False,
                actions=True, timeout=8, raise_errors=True)
            metadata = instrument.get_history_metadata()
        except Exception as exc:
            raise ProviderRequestError(f"Yahoo history unavailable: {type(exc).__name__}") from exc
        if metadata.get("currency") != "BRL" or metadata.get("symbol") != yahoo_symbol(ticker):
            raise ValueError("Yahoo identity or currency mismatch")
        now = datetime.now(timezone.utc)
        records = []
        for index, row in frame.iterrows():
            observed = index.to_pydatetime()
            if observed.tzinfo is None:
                raise ValueError("Yahoo history timezone missing")
            exchange_day = observed.date()
            if not start <= exchange_day <= end:
                continue
            values = [finite(row.get(field)) for field in ("Open", "High", "Low", "Close", "Volume")]
            if any(v is None or v < 0 for v in values) or min(values[:4]) <= 0:
                raise ValueError("Yahoo invalid OHLCV")
            opening, high, low, close, volume = values
            if not low <= min(opening, close) <= max(opening, close) <= high:
                raise ValueError("Yahoo inconsistent OHLC")
            records.append(StockMarketData(instrument_id=ticker.upper(), ticker=ticker.upper(),
                observation_timestamp=observed.astimezone(timezone.utc), available_timestamp=now,
                source=self.name, ingested_at=now, source_record_id=f"{yahoo_symbol(ticker)}:1d:{exchange_day}",
                quality_status="WARNING", quality_flags=("availability_is_ingestion_time", "daily_candle_not_current_quote", "auto_adjust_false", "repair_false"),
                open=opening, high=high, low=low, close=close, volume=volume,
                adjusted_close=finite(row.get("Adj Close")), currency="BRL"))
        if not records:
            raise ValueError("Yahoo empty history")
        return records

    def _info(self, ticker):
        instrument = self._ticker(ticker)
        try:
            info = instrument.get_info()
        except Exception as exc:
            raise ProviderRequestError(f"Yahoo info unavailable: {type(exc).__name__}") from exc
        if not isinstance(info, dict) or info.get("symbol") != yahoo_symbol(ticker):
            raise ValueError("Yahoo info identity mismatch")
        return info

    def get_current_quote(self, ticker):
        info = self._info(ticker)
        if info.get("currency") != "BRL":
            raise ValueError("Yahoo quote currency mismatch")
        timestamp = finite(info.get("regularMarketTime"))
        if timestamp is None:
            raise ValueError("Yahoo quote provider timestamp missing")
        observed = datetime.fromtimestamp(timestamp, timezone.utc)
        now = datetime.now(timezone.utc)
        # Historical closing quotes are useful as history, not as a fresh
        # acquisition input. OPLAB gets the next chance for this capability.
        if not 0 <= (now-observed).total_seconds() <= 1800:
            raise ValueError("Yahoo current quote stale")
        values = [finite(info.get(key)) for key in ("regularMarketOpen", "regularMarketDayHigh", "regularMarketDayLow", "regularMarketPrice", "regularMarketVolume")]
        if any(v is None or v < 0 for v in values) or min(values[:4]) <= 0:
            raise ValueError("Yahoo current OHLCV missing or invalid")
        return StockMarketData(instrument_id=ticker.upper(), ticker=ticker.upper(),
            observation_timestamp=observed, available_timestamp=now, source=self.name,
            ingested_at=now, source_record_id=f"{yahoo_symbol(ticker)}:quote:{int(timestamp)}",
            quality_status="WARNING", quality_flags=("current_quote", "potentially_delayed", "not_executable_quote"),
            open=values[0], high=values[1], low=values[2], close=values[3], volume=values[4])

    def get_financial_data(self, ticker):
        info = self._info(ticker)
        quote_currency = info.get("currency")
        financial_currency = info.get("financialCurrency")
        quote_currency = quote_currency if isinstance(quote_currency, str) and re.fullmatch(r"[A-Z]{3}", quote_currency) else None
        financial_currency = financial_currency if isinstance(financial_currency, str) and re.fullmatch(r"[A-Z]{3}", financial_currency) else None
        now = datetime.now(timezone.utc)
        aliases = {"trailingPE": "priceEarnings", "trailingEps": "earningsPerShare", "trailingAnnualDividendYield": "dividendYield"}
        fields = FRACTIONS | MONEY | MULTIPLES | PER_SHARE | {"debtToEquity"}
        records = []
        for field in sorted(fields):
            value = finite(info.get(field))
            if value is None:
                continue
            # A B3 quote can be BRL while issuer statements are USD. Ratios
            # remain admissible; currency is determined per field, never FX
            # converted implicitly. Flattened info does not establish the
            # currency of EPS/book/cash per-share when those currencies differ.
            currency = financial_currency
            if field == "marketCap":
                currency = quote_currency
            elif field == "enterpriseValue" or field in PER_SHARE:
                if quote_currency != financial_currency:
                    continue
                currency = quote_currency
            if field in MONEY | PER_SHARE and currency is None:
                continue
            flags = ("availability_is_ingestion_time", "current_snapshot_not_historical_pit", "fiscal_period_not_verified")
            if quote_currency and financial_currency and quote_currency != financial_currency:
                flags += ("mixed_quote_and_statement_currencies",)
            if field in {"forwardPE", "forwardEps"}:
                flags += ("consensus_estimate_not_realized_result", "estimate_horizon_not_verified")
            metric = aliases.get(field, field)
            records.append(StockFundamental(instrument_id=ticker.upper(), ticker=ticker.upper(),
                observation_timestamp=now, available_timestamp=now, source=self.name, ingested_at=now,
                source_record_id=f"{yahoo_symbol(ticker)}:info:{field}:{now.isoformat()}",
                quality_status="WARNING", quality_flags=flags,
                metric=metric, value=value, unit=fundamental_unit(field, currency), period_type="CURRENT_SNAPSHOT"))
        if not records:
            raise ValueError("Yahoo fundamentals empty")
        return records

    def get_dividends(self, ticker, *, start=None, end=None):
        start = start or date.today()-timedelta(days=366)
        end = end or date.today()
        instrument = self._ticker(ticker)
        try:
            frame = instrument.history(start=start.isoformat(), end=(end+timedelta(days=1)).isoformat(),
                interval="1d", auto_adjust=False, repair=False, actions=True, timeout=8, raise_errors=True)
            metadata = instrument.get_history_metadata()
        except Exception as exc:
            raise ProviderRequestError(f"Yahoo dividends unavailable: {type(exc).__name__}") from exc
        if metadata.get("currency") != "BRL" or metadata.get("symbol", yahoo_symbol(ticker)) != yahoo_symbol(ticker):
            raise ValueError("Yahoo dividend currency or identity mismatch")
        now = datetime.now(timezone.utc)
        records = []
        for index, row in frame.iterrows():
            value = finite(row.get("Dividends"))
            if value is None or value <= 0 or not start <= index.date() <= end:
                continue
            records.append(DividendRecord(instrument_id=ticker.upper(), ticker=ticker.upper(),
                observation_timestamp=index.to_pydatetime().astimezone(timezone.utc), available_timestamp=now,
                source=self.name, ingested_at=now, source_record_id=f"{yahoo_symbol(ticker)}:distribution:{index.date()}:{value}",
                quality_status="WARNING", quality_flags=("availability_is_ingestion_time", "payment_date_unknown", "dividend_or_jcp_type_unknown"),
                payment_type="UNKNOWN", ex_date=index.date(), gross_amount=value))
        return records
