from datetime import datetime, timezone
import json
import os
import urllib.request

from b3_agent.schemas.option import OptionQuote


class OplabOptionQuoteAdapter:
    """Adapter for OPLAB current option quotes."""

    BASE_URL = "https://api.oplab.com.br/v3"

    @property
    def name(self) -> str:
        return "oplab"

    def get_option_quotes(
        self,
        ticker: str,
        as_of: datetime,
    ) -> list[OptionQuote]:
        """Retrieve current option quotes for an underlying."""

        ticker = ticker.upper().strip()

        if not ticker:
            raise ValueError("ticker must not be empty")

        token = os.getenv("OPLAB_API_TOKEN")

        if not token:
            raise RuntimeError(
                "OPLAB_API_TOKEN environment variable is not set"
            )

        url = f"{self.BASE_URL}/market/options/{ticker}"

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

        if not isinstance(payload, list):
            raise ValueError(
                f"oplab returned an unexpected options response for {ticker}"
            )

        ingested_at = datetime.now(timezone.utc)
        records: list[OptionQuote] = []

        for item in payload:
            option_id = item.get("symbol")

            if not option_id:
                raise ValueError(
                    f"oplab option response for {ticker} is missing symbol"
                )

            bid = (
                float(item["bid"])
                if item.get("bid") is not None
                and float(item["bid"]) > 0
                else None
            )

            ask = (
                float(item["ask"])
                if item.get("ask") is not None
                and float(item["ask"]) > 0
                else None
            )

            last = (
                float(item["close"])
                if item.get("close") is not None
                and float(item["close"]) > 0
                else None
            )

            mid = (
                (bid + ask) / 2
                if bid is not None and ask is not None
                else None
            )

            volume = float(item.get("volume") or 0)

            if item.get("time") is not None:
                observation_timestamp = datetime.fromtimestamp(
                    float(item["time"]) / 1000,
                    tz=timezone.utc,
                )
            else:
                observation_timestamp = ingested_at

            records.append(
                OptionQuote(
                    instrument_id=str(option_id),
                    ticker=str(option_id),
                    option_id=str(option_id),
                    bid=bid,
                    ask=ask,
                    last=last,
                    mid=mid,
                    volume=volume,
                    open_interest=None,
                    implied_volatility=None,
                    delta=None,
                    gamma=None,
                    theta=None,
                    vega=None,
                    rho=None,
                    observation_timestamp=observation_timestamp,
                    available_timestamp=ingested_at,
                    source=self.name,
                    ingested_at=ingested_at,
                    source_record_id=(
                        f"{option_id}:{item.get('time', int(ingested_at.timestamp() * 1000))}"
                    ),
                )
            )

        return records
