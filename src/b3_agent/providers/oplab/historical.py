from __future__ import annotations

from datetime import date, datetime, timezone
import os
import urllib.parse
import urllib.request

from b3_agent.providers.http_retry import request_json
from b3_agent.schemas.market import StockMarketData


class OplabHistoricalAdapter:
    """OPLAB daily historical-market adapter.

    Uses the validated market/historical symbol endpoint at daily resolution
    and normalizes OHLCV candles into the canonical StockMarketData schema.
    Historical availability is conservatively set to ingestion time because the
    provider payload does not expose a reliable publication timestamp.
    """

    BASE_URL = "https://api.oplab.com.br/v3"

    def __init__(self, *, resolution: str = "1d") -> None:
        if resolution != "1d":
            raise ValueError("canonical market history currently supports resolution=1d")
        self.resolution = resolution

    @property
    def name(self) -> str:
        return "oplab"

    def get_market_data(
        self,
        ticker: str,
        start: date,
        end: date,
    ) -> list[StockMarketData]:
        normalized = ticker.upper().strip()
        if not normalized:
            raise ValueError("ticker must not be empty")
        if start > end:
            raise ValueError("start date must be on or before end date")

        token = os.getenv("OPLAB_API_TOKEN")
        if not token:
            raise RuntimeError("OPLAB_API_TOKEN environment variable is not set")

        amount = max(5, (end - start).days + 10)
        query = urllib.parse.urlencode({"amount": amount})
        url = (
            f"{self.BASE_URL}/market/historical/"
            f"{urllib.parse.quote(normalized)}/{self.resolution}?{query}"
        )
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
            provider="oplab",
            timeout_env="B3_OPLAB_TIMEOUT_SECONDS",
            default_timeout=30.0,
            retry_http_codes={408, 425, 429, 500, 502, 503, 504},
            opener=urllib.request.urlopen,
        )

        if not isinstance(payload, dict):
            raise ValueError(
                f"oplab returned an unexpected historical response for {normalized}"
            )
        symbol = str(payload.get("symbol") or "").upper().strip()
        resolution = str(payload.get("resolution") or "").strip()
        data = payload.get("data")
        if symbol and symbol != normalized:
            raise ValueError(
                f"oplab historical identity mismatch: requested {normalized}, got {symbol}"
            )
        if resolution and resolution != self.resolution:
            raise ValueError(
                f"oplab historical resolution mismatch: expected {self.resolution}, got {resolution}"
            )
        if not isinstance(data, list):
            raise ValueError(
                f"oplab returned invalid historical data for {normalized}"
            )

        ingested_at = datetime.now(timezone.utc)
        records: list[StockMarketData] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            required = {
                "time": item.get("time"),
                "open": item.get("open"),
                "high": item.get("high"),
                "low": item.get("low"),
                "close": item.get("close"),
                "volume": item.get("volume"),
            }
            missing = [key for key, value in required.items() if value is None]
            if missing:
                raise ValueError(
                    f"oplab historical response for {normalized} is missing "
                    f"required fields: {', '.join(missing)}"
                )

            observed = datetime.fromtimestamp(
                float(required["time"]) / 1000.0,
                tz=timezone.utc,
            )
            if not start <= observed.date() <= end:
                continue

            records.append(
                StockMarketData(
                    instrument_id=normalized,
                    ticker=normalized,
                    observation_timestamp=observed,
                    available_timestamp=ingested_at,
                    source=self.name,
                    ingested_at=ingested_at,
                    source_record_id=(
                        f"{normalized}:{self.resolution}:{int(float(required['time']))}"
                    ),
                    quality_status="VALID",
                    quality_flags=("availability_is_ingestion_time",),
                    open=float(required["open"]),
                    high=float(required["high"]),
                    low=float(required["low"]),
                    close=float(required["close"]),
                    volume=float(required["volume"]),
                    currency="BRL",
                )
            )

        records.sort(key=lambda item: item.observation_timestamp)
        if not records:
            raise ValueError(
                f"oplab returned no historical data for {normalized} in requested range"
            )
        return records


__all__ = ["OplabHistoricalAdapter"]
