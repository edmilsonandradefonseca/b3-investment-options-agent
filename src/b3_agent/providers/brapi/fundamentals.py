from __future__ import annotations

from datetime import date, datetime, time, timezone
import json
import os
from typing import Any
from urllib.error import HTTPError
import urllib.parse
import urllib.request

from b3_agent.schemas.dividend import DividendRecord
from b3_agent.schemas.fundamental import StockFundamental


class BrapiFundamentalsAdapter:
    """BRAPI fundamentals adapter with a capability-aware quote fallback.

    The preferred source remains the v2 financial-data endpoint. Some BRAPI
    plans allow authenticated quotes for a ticker while denying the richer
    financial-data module with HTTP 403. In that case the adapter falls back to
    the documented v1 quote fields that are genuinely available (marketCap,
    priceEarnings and earningsPerShare) instead of reporting all fundamentals as
    unavailable.

    Historical availability timestamps are never inferred.
    """

    BASE_URL = "https://brapi.dev/api/v2/stocks"
    QUOTE_URL = "https://brapi.dev/api/quote"

    @property
    def name(self) -> str:
        return "brapi"

    def get_financial_data(self, ticker: str) -> list[StockFundamental]:
        normalized = self._ticker(ticker)
        try:
            item = self._single_result("financial-data", normalized)
        except HTTPError as exc:
            if exc.code != 403:
                raise
            return self._quote_basic_fundamentals(normalized)

        data = item.get("data") or {}
        if not isinstance(data, dict):
            raise ValueError(
                f"brapi returned invalid financial data for {normalized}"
            )

        ingested_at = datetime.now(timezone.utc)
        updated_at = _parse_datetime(data.get("updatedAt")) or ingested_at
        records: list[StockFundamental] = []
        for field, value in sorted(data.items()):
            if field in {"symbol", "type", "updatedAt", "financialCurrency"}:
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            records.append(
                StockFundamental(
                    instrument_id=normalized,
                    ticker=normalized,
                    observation_timestamp=updated_at,
                    available_timestamp=ingested_at,
                    source=self.name,
                    ingested_at=ingested_at,
                    source_record_id=(
                        f"{normalized}:financial-data:{field}:"
                        f"{updated_at.isoformat()}"
                    ),
                    quality_status="WARNING",
                    quality_flags=("availability_is_ingestion_time",),
                    metric=field,
                    value=float(value),
                    report_date=updated_at.date(),
                    period_type="TTM",
                    unit=_fundamental_unit(
                        field,
                        data.get("financialCurrency"),
                    ),
                )
            )

        if not records:
            raise ValueError(
                f"brapi returned no numeric financial metrics for {normalized}"
            )
        return records

    def _quote_basic_fundamentals(
        self,
        ticker: str,
    ) -> list[StockFundamental]:
        request = urllib.request.Request(
            f"{self.QUOTE_URL}/{urllib.parse.quote(ticker)}",
            headers=self._headers(),
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))

        if not isinstance(payload, dict):
            raise ValueError(
                f"brapi returned invalid quote fallback for {ticker}"
            )
        results = payload.get("results") or []
        if not isinstance(results, list) or not results:
            raise ValueError(
                f"brapi returned no quote fallback result for {ticker}"
            )
        item = next(
            (
                result
                for result in results
                if str(result.get("symbol", "")).upper() == ticker
            ),
            results[0],
        )
        if not isinstance(item, dict):
            raise ValueError(
                f"brapi returned invalid quote fallback item for {ticker}"
            )

        ingested_at = datetime.now(timezone.utc)
        observed_at = (
            _parse_datetime(item.get("regularMarketTime"))
            or _parse_datetime(payload.get("requestedAt"))
            or ingested_at
        )
        currency = item.get("currency") or "BRL"
        fields = ("marketCap", "priceEarnings", "earningsPerShare")
        records: list[StockFundamental] = []
        for field in fields:
            value = item.get(field)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            records.append(
                StockFundamental(
                    instrument_id=ticker,
                    ticker=ticker,
                    observation_timestamp=observed_at,
                    available_timestamp=ingested_at,
                    source=self.name,
                    ingested_at=ingested_at,
                    source_record_id=(
                        f"{ticker}:quote-fallback:{field}:"
                        f"{observed_at.isoformat()}"
                    ),
                    quality_status="WARNING",
                    quality_flags=(
                        "availability_is_ingestion_time",
                        "brapi_quote_fallback",
                    ),
                    metric=field,
                    value=float(value),
                    report_date=observed_at.date(),
                    period_type=(
                        "CURRENT" if field == "marketCap" else "TTM"
                    ),
                    unit=_fundamental_unit(field, currency),
                )
            )

        if not records:
            raise ValueError(
                f"brapi quote fallback returned no basic fundamentals for {ticker}"
            )
        return records

    def get_dividends(
        self,
        ticker: str,
        *,
        start: date | None = None,
        end: date | None = None,
    ) -> list[DividendRecord]:
        normalized = self._ticker(ticker)
        params: dict[str, str] = {
            "symbols": normalized,
            "sortOrder": "asc",
        }
        if start is not None:
            params["startDate"] = start.isoformat()
        if end is not None:
            params["endDate"] = end.isoformat()

        try:
            payload = self._get("dividends", params)
        except HTTPError as exc:
            if exc.code != 403:
                raise
            # Documented legacy quote module, with the same Bearer credential.
            query = urllib.parse.urlencode({"dividends": "true"})
            request = urllib.request.Request(
                f"{self.QUOTE_URL}/{urllib.parse.quote(normalized)}?{query}",
                headers=self._headers(),
            )
            with urllib.request.urlopen(request, timeout=20) as response:
                legacy = json.loads(response.read().decode("utf-8"))
            exact = next((item for item in legacy.get("results", []) if str(item.get("symbol", "")).upper() == normalized), None)
            if exact is None or not isinstance(exact.get("dividendsData"), dict):
                raise ValueError("BRAPI quote dividend module unavailable for exact ticker")
            payload = {"results": [{"symbol": normalized, "data": exact["dividendsData"]}]}

        results = payload.get("results") or []
        if not results:
            raise ValueError(
                f"brapi returned no dividend result for {normalized}"
            )

        item = next(
            (
                result
                for result in results
                if str(result.get("symbol", "")).upper() == normalized
            ),
            None,
        )
        if item is None:
            raise ValueError("BRAPI dividends unavailable for exact ticker")
        data = item.get("data") or {}
        cash = data.get("cashDividends") or []
        ingested_at = datetime.now(timezone.utc)
        records: list[DividendRecord] = []

        for index, event in enumerate(cash):
            rate = event.get("rate")
            if rate is None:
                continue
            approved_on = _parse_date(event.get("approvedOn"))
            ex_date = _parse_date(event.get("exDate"))
            last_date_prior = _parse_date(event.get("lastDatePrior"))
            payment_date = _parse_date(event.get("paymentDate"))
            observed_date = (
                approved_on
                or last_date_prior
                or ex_date
                or payment_date
            )
            observed_at = (
                datetime.combine(
                    observed_date,
                    time.min,
                    tzinfo=timezone.utc,
                )
                if observed_date is not None
                else ingested_at
            )
            event_id = (
                event.get("isinCode")
                or event.get("assetIssued")
                or normalized
            )
            records.append(
                DividendRecord(
                    instrument_id=normalized,
                    ticker=normalized,
                    observation_timestamp=observed_at,
                    available_timestamp=ingested_at,
                    source=self.name,
                    ingested_at=ingested_at,
                    source_record_id=(
                        f"{normalized}:dividend:{event_id}:{index}:"
                        f"{approved_on or ex_date or payment_date}"
                    ),
                    quality_status="WARNING",
                    quality_flags=("availability_is_ingestion_time",),
                    payment_type=str(
                        event.get("label") or "CASH_DISTRIBUTION"
                    ).upper(),
                    announcement_date=approved_on,
                    ex_date=ex_date,
                    record_date=last_date_prior,
                    payment_date=payment_date,
                    gross_amount=float(rate),
                    currency="BRL",
                    reference_period=(
                        str(event.get("relatedTo"))
                        if event.get("relatedTo") is not None
                        else None
                    ),
                )
            )
        return records

    def _single_result(
        self,
        endpoint: str,
        ticker: str,
    ) -> dict[str, Any]:
        payload = self._get(endpoint, {"symbols": ticker})
        results = payload.get("results") or []
        if not results:
            raise ValueError(
                f"brapi returned no {endpoint} result for {ticker}"
            )
        return next(
            (
                result
                for result in results
                if str(result.get("symbol", "")).upper() == ticker
            ),
            results[0],
        )

    def _get(
        self,
        endpoint: str,
        params: dict[str, str],
    ) -> dict[str, Any]:
        query = urllib.parse.urlencode(params)
        request = urllib.request.Request(
            f"{self.BASE_URL}/{endpoint}?{query}",
            headers=self._headers(),
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

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

    @staticmethod
    def _ticker(ticker: str) -> str:
        normalized = ticker.upper().strip()
        if not normalized:
            raise ValueError("ticker must not be empty")
        return normalized


def _parse_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _parse_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _fundamental_unit(
    field: str,
    currency: Any,
) -> str | None:
    normalized = field.casefold()
    if (
        "margin" in normalized
        or "ratio" in normalized
        or normalized == "priceearnings"
    ):
        return "ratio"
    if normalized.endswith("pershare"):
        return str(currency or "BRL") + "/share"
    if normalized == "marketcap":
        return str(currency or "BRL")
    if any(
        token in normalized
        for token in (
            "revenue",
            "ebitda",
            "profit",
            "cash",
            "debt",
            "income",
            "flow",
            "expense",
            "assets",
            "liabilities",
            "equity",
        )
    ):
        return str(currency or "BRL")
    return None
