from datetime import datetime, timezone
import os
import urllib.request

from b3_agent.providers.http_retry import request_json

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
        payload = request_json(
            request,
            provider="oplab",
            timeout_env="B3_OPLAB_TIMEOUT_SECONDS",
            default_timeout=30.0,
            retry_http_codes={408, 425, 429, 500, 502, 503, 504},
            opener=urllib.request.urlopen,
        )

        if not isinstance(payload, list):
            raise ValueError(
                f"oplab returned an unexpected options response for {ticker}"
            )
        return payload

    def get_options(self, ticker: str, as_of: datetime) -> list[OptionContract]:
        """Retrieve the current option chain for an underlying."""
        ticker = ticker.upper().strip()
        return self._parse_options(ticker, self._get_payload(ticker))

    def get_snapshot(self, ticker: str, as_of: datetime) -> tuple[list[OptionContract], list[OptionQuote]]:
        """Retrieve contracts and quotes from one consistent provider response."""
        ticker = ticker.upper().strip()
        payload = self._get_payload(ticker)
        ingested_at = datetime.now(timezone.utc)
        return (
            self._parse_options(ticker, payload),
            self._parse_quotes(ticker, as_of, payload, ingested_at),
        )

    def _parse_options(self, ticker: str, payload: list[dict]) -> list[OptionContract]:
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
        """Normalize current option quotes from the OPLAB option chain."""
        ticker = ticker.upper().strip()
        payload = self._get_payload(ticker)
        ingested_at = datetime.now(timezone.utc)
        return self._parse_quotes(ticker, as_of, payload, ingested_at)

    def get_current_option_quote(
        self,
        ticker: str,
        option_id: str,
        as_of: datetime,
    ) -> OptionQuote:
        """Return one explicit current option quote from the OPLAB chain."""
        normalized_ticker = ticker.upper().strip()
        normalized_option = option_id.upper().strip()
        if not normalized_option:
            raise ValueError("option_id must not be empty")
        quotes = self.get_option_quotes(normalized_ticker, as_of)
        match = next(
            (
                quote
                for quote in quotes
                if quote.option_id.upper() == normalized_option
            ),
            None,
        )
        if match is None:
            raise ValueError(
                f"oplab returned no current quote for option {normalized_option}"
            )
        return match

    def _parse_quotes(
        self, ticker: str, as_of: datetime, payload: list[dict], ingested_at: datetime
    ) -> list[OptionQuote]:
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

            def positive_number(*keys: str) -> float | None:
                value = number(*keys)
                return value if value is not None and value > 0 else None

            bid = positive_number("bid")
            ask = positive_number("ask")
            last = positive_number("last", "close")
            mid = positive_number("mid")
            if mid is None and bid is not None and ask is not None:
                mid = (bid + ask) / 2.0

            provider_time = item.get("time")
            observation_timestamp = as_of
            if provider_time is not None:
                observation_timestamp = datetime.fromtimestamp(
                    float(provider_time) / 1000.0,
                    tz=timezone.utc,
                )

            quotes.append(
                OptionQuote(
                    instrument_id=str(option_id),
                    ticker=ticker,
                    observation_timestamp=observation_timestamp,
                    available_timestamp=ingested_at,
                    source=self.name,
                    ingested_at=ingested_at,
                    source_record_id=(
                        f"{ticker}:{option_id}:"
                        f"{int(float(provider_time)) if provider_time is not None else as_of.isoformat()}"
                    ),
                    option_id=str(option_id),
                    bid=bid,
                    ask=ask,
                    last=last,
                    mid=mid,
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
