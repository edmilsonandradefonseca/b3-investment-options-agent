from datetime import date, datetime, timezone
import json
import os
import urllib.request

from b3_agent.schemas.market import StockMarketData


class OplabAdapter:
    """Adapter for OPLAB stock market data."""

    BASE_URL = "https://api.oplab.com.br/v3"

    @property
    def name(self) -> str:
        return "oplab"

    def get_market_data(
        self,
        ticker: str,
        start: date,
        end: date,
    ) -> list[StockMarketData]:
        """Retrieve current stock market data from OPLAB."""

        ticker = ticker.upper().strip()

        if not ticker:
            raise ValueError("ticker must not be empty")

        if start > end:
            raise ValueError("start date must be on or before end date")

        token = os.getenv("OPLAB_API_TOKEN")

        if not token:
            raise RuntimeError("OPLAB_API_TOKEN environment variable is not set")

        url = f"{self.BASE_URL}/market/stocks/{ticker}"

        request = urllib.request.Request(
            url,
            headers={
                "Access-Token": token,
                "User-Agent": "b3-investment-options-agent/0.1",
                "Accept": "application/json",
            },
        )

        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))

        required_fields = {
            "open": payload.get("open"),
            "high": payload.get("high"),
            "low": payload.get("low"),
            "close": payload.get("close"),
            "volume": payload.get("volume"),
        }

        missing = [
            field
            for field, value in required_fields.items()
            if value is None
        ]

        if missing:
            raise ValueError(
                f"oplab response for {ticker} is missing required fields: "
                f"{', '.join(missing)}"
            )

        observation_timestamp = (
            datetime.fromtimestamp(
                float(payload["time"]) / 1000,
                tz=timezone.utc,
            )
            if payload.get("time") is not None
            else datetime.now(timezone.utc)
        )

        ingested_at = datetime.now(timezone.utc)

        return [
            StockMarketData(
                instrument_id=ticker,
                ticker=ticker,
                observation_timestamp=observation_timestamp,
                available_timestamp=ingested_at,
                source=self.name,
                ingested_at=ingested_at,
                source_record_id=(
                    f"{ticker}:{payload.get('time', int(ingested_at.timestamp() * 1000))}"
                ),
                open=float(payload["open"]),
                high=float(payload["high"]),
                low=float(payload["low"]),
                close=float(payload["close"]),
                volume=float(payload["volume"]),
                currency="BRL",
            )
        ]
