from datetime import date, datetime, timezone
import os
import math
from threading import local
import urllib.request

from b3_agent.providers.http_retry import request_json
from b3_agent.schemas.market import StockMarketData
from b3_agent.intelligence.reuse import ContextReuse, fingerprint

_CURRENT_QUOTES = ContextReuse(capacity=128, ttl_seconds=5)


class OplabAdapter:
    """Adapter for OPLAB stock market data."""

    BASE_URL = "https://api.oplab.com.br/v3"

    def __init__(self):
        self._acquisition = local()

    @property
    def last_reuse_telemetry(self):
        return getattr(self._acquisition, "telemetry", {})

    @property
    def name(self) -> str:
        return "oplab"

    def get_current_quote(self, ticker: str) -> StockMarketData:
        """Retrieve the current stock quote from OPLAB.

        This is intentionally separate from historical candles. The returned
        record represents the provider's latest stock-market observation at the
        time of the request and must not be used as a historical series.
        """
        ticker = ticker.upper().strip()
        if not ticker:
            raise ValueError("ticker must not be empty")

        token = os.getenv("OPLAB_API_TOKEN")
        if not token:
            raise RuntimeError("OPLAB_API_TOKEN environment variable is not set")

        key = (fingerprint(["oplab-stock-current-v1", self.BASE_URL, ticker, token]), urllib.request.urlopen)
        quote, telemetry = _CURRENT_QUOTES.get_or_build(key, lambda: self._fetch_current_quote(ticker, token))
        self._acquisition.telemetry = {**telemetry, "source": self.name, "ticker": ticker, "ttl_seconds": 5}
        return quote

    def _fetch_current_quote(self, ticker: str, token: str) -> StockMarketData:
        url = f"{self.BASE_URL}/market/stocks/{ticker}"
        request = urllib.request.Request(
            url,
            headers={
                "Access-Token": token,
                "User-Agent": "b3-investment-options-agent/0.1",
                "Accept": "application/json",
            },
        )

        payload = request_json(
            request,
            provider="oplab-stock",
            timeout_env="B3_OPLAB_TIMEOUT_SECONDS",
            default_timeout=15.0,
            default_attempts=2,
            opener=urllib.request.urlopen,
        )

        if not isinstance(payload, dict):
            raise ValueError(f"oplab returned invalid stock quote for {ticker}")
        returned_symbol = str(payload.get("symbol") or ticker).upper().strip()
        if returned_symbol != ticker:
            raise ValueError(
                f"oplab stock quote identity mismatch: requested {ticker}, got {returned_symbol}"
            )

        required_fields = {
            "open": payload.get("open"),
            "high": payload.get("high"),
            "low": payload.get("low"),
            "close": payload.get("close"),
            "volume": payload.get("volume"),
        }
        missing = [field for field, value in required_fields.items() if value is None]
        if missing:
            raise ValueError(
                f"oplab response for {ticker} is missing required fields: "
                f"{', '.join(missing)}"
            )

        if any(not math.isfinite(float(value)) or float(value) < 0 for value in required_fields.values()):
            raise ValueError("oplab stock quote contains invalid numeric fields")

        ingested_at = datetime.now(timezone.utc)
        observation_timestamp = (
            datetime.fromtimestamp(
                float(payload["time"]) / 1000,
                tz=timezone.utc,
            )
            if payload.get("time") is not None
            else ingested_at
        )

        return StockMarketData(
            instrument_id=ticker,
            ticker=ticker,
            observation_timestamp=observation_timestamp,
            available_timestamp=ingested_at,
            source=self.name,
            ingested_at=ingested_at,
            source_record_id=(
                f"{ticker}:current:"
                f"{payload.get('time', int(ingested_at.timestamp() * 1000))}"
            ),
            quality_status="VALID",
            quality_flags=("current_quote",) + (("provider_timestamp_missing",) if payload.get("time") is None else ()),
            open=float(payload["open"]),
            high=float(payload["high"]),
            low=float(payload["low"]),
            close=float(payload["close"]),
            volume=float(payload["volume"]),
            currency="BRL",
        )

    def get_market_data(
        self,
        ticker: str,
        start: date,
        end: date,
    ) -> list[StockMarketData]:
        """Backward-compatible current-quote wrapper.

        Historical callers should use OplabHistoricalAdapter instead.
        """
        if start > end:
            raise ValueError("start date must be on or before end date")
        return [self.get_current_quote(ticker)]
