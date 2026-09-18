from datetime import datetime, timezone
import json
import os
import urllib.request

from b3_agent.schemas.option import OptionContract, OptionQuote


class OplabOptionsAdapter:
    """Adapter for OPLAB current option-chain data."""

    BASE_URL = "https://api.oplab.com.br/v3"

    @property
    def name(self) -> str:
        return "oplab"

    def _get_payload(self, ticker: str) -> list[dict]:
        ticker = ticker.upper().strip()
        if not ticker:
            raise ValueError("ticker must not be empty")

        token = os.getenv("OPLAB_API_TOKEN")
        if not token:
            raise RuntimeError("OPLAB_API_TOKEN environment variable is not set")

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
        return payload

    def get_options(self, ticker: str, as_of: datetime) -> list[OptionContract]:
        """Retrieve the current option chain for an underlying."""
        ticker = ticker.upper().strip()
        payload = self._get_payload(ticker)
        records: list[OptionContract] = []

        for item in payload:
            required_fields = {
                "symbol": item.get("symbol"),
                "type": item.get("type"),
                "strike": item.get("strike"),
                "due_date": item.get("due_date"),
            }
            missing = [field for field, value in required_fields.items() if value is None]
            if missing:
                raise ValueError(
                    f"oplab option response for {ticker} is missing required fields: "
                    f"{', '.join(missing)}"
                )

            option_type = str(item["type"]).upper()
            if option_type not in {"CALL", "PUT"}:
                raise ValueError(f"oplab returned unsupported option type: {option_type}")

            expiration_date = datetime.fromisoformat(
                str(item["due_date"]).replace("Z", "+00:00")
            ).date()
            option_id = str(item["symbol"])
            records.append(
                OptionContract(
                    option_id=option_id,
                    underlying_id=ticker,
                    underlying_ticker=ticker,
                    option_ticker=option_id,
                    option_type=option_type,
                    strike=float(item["strike"]),
                    expiration_date=expiration_date,
                    exercise_style=item.get("maturity_type"),
                    contract_multiplier=float(item.get("contract_size") or 1),
                    currency="BRL",
                )
            )
        return records

    def get_option_quotes(self, ticker: str, as_of: datetime) -> list[OptionQuote]:
        """Normalize quote fields from the same OPLAB option-chain response."""
        ticker = ticker.upper().strip()
        payload = self._get_payload(ticker)
        ingested_at = datetime.now(timezone.utc)
        quotes: list[OptionQuote] = []

        for item in payload:
            option_id = item.get("symbol")
            if option_id is None:
                raise ValueError(f"oplab option response for {ticker} is missing symbol")

            def number(*keys: str) -> float | None:
                for key in keys:
                    value = item.get(key)
                    if value is not None:
                        return float(value)
                return None

            quotes.append(
                OptionQuote(
                    instrument_id=str(option_id),
                    ticker=ticker,
                    observation_timestamp=as_of,
                    available_timestamp=ingested_at,
                    source=self.name,
                    ingested_at=ingested_at,
                    source_record_id=f"{ticker}:{option_id}:{as_of.isoformat()}",
                    option_id=str(option_id),
                    bid=number("bid"),
                    ask=number("ask"),
                    last=number("last", "close"),
                    mid=number("mid"),
                    volume=number("volume") or 0.0,
                    open_interest=number("open_interest"),
                    implied_volatility=number("implied_volatility", "iv"),
                    delta=number("delta"),
                    gamma=number("gamma"),
                    theta=number("theta"),
                    vega=number("vega"),
                    rho=number("rho"),
                )
            )
        return quotes
