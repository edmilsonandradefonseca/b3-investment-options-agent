from datetime import date, datetime, timezone
import os
import urllib.parse
import urllib.request
import math

from b3_agent.providers.http_retry import request_json

from b3_agent.schemas.market import StockMarketData


class BrapiAdapter:
    """Adapter for BRAPI stock market data."""

    BASE_URL = "https://brapi.dev/api"

    @property
    def name(self) -> str:
        return "brapi"

    def get_current_quote(self, ticker: str) -> StockMarketData:
        normalized = ticker.strip().upper()
        if not normalized:
            raise ValueError("ticker must not be empty")
        request = urllib.request.Request(f"{self.BASE_URL}/quote/{urllib.parse.quote(normalized)}", headers=self._headers())
        payload = request_json(request, provider="brapi", timeout_env="B3_BRAPI_TIMEOUT_SECONDS",
            default_timeout=10, default_attempts=1, opener=urllib.request.urlopen)
        rows = payload.get("results", [])
        item = next((row for row in rows if row.get("symbol") == normalized), None)
        if item is None or item.get("currency") != "BRL":
            raise ValueError("BRAPI current quote identity or currency mismatch")
        raw_time = item.get("regularMarketTime")
        if isinstance(raw_time, str):
            observed = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
        elif isinstance(raw_time, (int, float)) and not isinstance(raw_time, bool):
            observed = datetime.fromtimestamp(raw_time, timezone.utc)
        else:
            raise ValueError("BRAPI quote timestamp missing")
        if observed.tzinfo is None:
            raise ValueError("BRAPI quote timezone missing")
        values = [item.get(key) for key in ("regularMarketOpen", "regularMarketDayHigh", "regularMarketDayLow", "regularMarketPrice", "regularMarketVolume")]
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for v in values) or min(values[:4]) <= 0:
            raise ValueError("BRAPI current OHLCV invalid")
        now = datetime.now(timezone.utc)
        return StockMarketData(instrument_id=normalized, ticker=normalized,
            observation_timestamp=observed, available_timestamp=now, source=self.name, ingested_at=now,
            source_record_id=f"{normalized}:quote:{observed.isoformat()}",
            quality_status="WARNING", quality_flags=("current_quote", "potentially_delayed", "not_executable_quote"),
            open=values[0], high=values[1], low=values[2], close=values[3], volume=values[4])

    def get_market_data(
        self,
        ticker: str,
        start: date,
        end: date,
    ) -> list[StockMarketData]:
        """Retrieve historical daily market data from BRAPI."""

        ticker = ticker.upper().strip()

        if not ticker:
            raise ValueError("ticker must not be empty")

        if start > end:
            raise ValueError("start date must be on or before end date")

        query = urllib.parse.urlencode(
            {
                "symbols": ticker,
                "startDate": start.isoformat(),
                "endDate": end.isoformat(),
                "interval": "1d",
                "sortOrder": "asc",
            }
        )

        url = f"{self.BASE_URL}/v2/stocks/historical?{query}"

        request = urllib.request.Request(
            url,
            headers=self._headers(),
        )

        payload = request_json(
            request,
            provider="brapi",
            timeout_env="B3_BRAPI_TIMEOUT_SECONDS",
            default_timeout=20.0,
            retry_http_codes={404, 408, 425, 429, 500, 502, 503, 504},
            opener=urllib.request.urlopen,
        )

        results = payload.get("results", [])

        if not results:
            raise ValueError(
                f"brapi returned no market data for ticker {ticker}"
            )

        result = results[0]
        historical_data = result.get("data", {}).get(
            "historicalDataPrice", []
        )

        if not historical_data:
            raise ValueError(
                f"brapi returned no historical data for ticker {ticker}"
            )

        ingested_at = datetime.now(timezone.utc)
        records: list[StockMarketData] = []

        for item in historical_data:
            required_fields = {
                "date": item.get("date"),
                "open": item.get("open"),
                "high": item.get("high"),
                "low": item.get("low"),
                "close": item.get("close"),
                "volume": item.get("volume"),
            }

            missing = [
                field
                for field, value in required_fields.items()
                if value is None
            ]

            if missing:
                raise ValueError(
                    f"brapi historical response for {ticker} is missing "
                    f"required fields: {', '.join(missing)}"
                )

            observation_timestamp = datetime.fromtimestamp(
                float(required_fields["date"]),
                tz=timezone.utc,
            )

            records.append(
                StockMarketData(
                    instrument_id=ticker,
                    ticker=ticker,
                    observation_timestamp=observation_timestamp,
                    available_timestamp=ingested_at,
                    source=self.name,
                    ingested_at=ingested_at,
                    source_record_id=(
                        f"{ticker}:{int(required_fields['date'])}"
                    ),
                    open=float(required_fields["open"]),
                    high=float(required_fields["high"]),
                    low=float(required_fields["low"]),
                    close=float(required_fields["close"]),
                    volume=float(required_fields["volume"]),
                    currency="BRL",
                )
            )

        return records

    @staticmethod
    def _headers() -> dict[str, str]:
        headers = {
            "User-Agent": "b3-investment-options-agent/0.1",
            "Accept": "application/json",
        }
        token = os.getenv("BRAPI_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers
