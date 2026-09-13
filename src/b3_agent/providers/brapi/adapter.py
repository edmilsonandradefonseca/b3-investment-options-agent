from datetime import datetime, timezone
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
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> StockMarketData:
        """Retrieve market data from BRAPI and map it to our data contract."""

        ticker = ticker.upper().strip()

        if not ticker:
            raise ValueError("ticker must not be empty")

        url = f"{self.BASE_URL}/quote/{urllib.parse.quote(ticker)}"

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

        quote = results[0]

        required_fields = {
            "regularMarketOpen": quote.get("regularMarketOpen"),
            "regularMarketDayHigh": quote.get("regularMarketDayHigh"),
            "regularMarketDayLow": quote.get("regularMarketDayLow"),
            "regularMarketPrice": quote.get("regularMarketPrice"),
            "regularMarketVolume": quote.get("regularMarketVolume"),
        }

        missing = [
            field
            for field, value in required_fields.items()
            if value is None
        ]

        if missing:
            raise ValueError(
                f"brapi response for {ticker} is missing required fields: "
                f"{', '.join(missing)}"
            )

        now = datetime.now(timezone.utc)

        return StockMarketData(
            instrument_id=ticker,
            ticker=ticker,
            observation_timestamp=now,
            available_timestamp=now,
            source=self.name,
            ingested_at=now,
            open=float(required_fields["regularMarketOpen"]),
            high=float(required_fields["regularMarketDayHigh"]),
            low=float(required_fields["regularMarketDayLow"]),
            close=float(required_fields["regularMarketPrice"]),
            volume=float(required_fields["regularMarketVolume"]),
            currency="BRL",
        )