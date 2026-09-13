from datetime import date, datetime, timezone
import json
import urllib.parse
import urllib.request

from b3_agent.schemas.market import StockMarketData


class BrapiAdapter:
    """Adapter for BRAPI stock market data."""

    BASE_URL = "https://brapi.dev/api"

    @property
    def name(self) -> str:
        return "brapi"

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
            headers={
                "User-Agent": "b3-investment-options-agent/0.1",
                "Accept": "application/json",
            },
        )

        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))

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
