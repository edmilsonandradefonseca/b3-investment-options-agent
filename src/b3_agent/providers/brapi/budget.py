"""One conservative, process-shared reservation per BRAPI HTTP attempt.

An allowance must be configured explicitly. This is a local budget, not a
claim about the account balance: other clients may consume the same account.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
import os
import sqlite3
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from b3_agent.config import settings

_REASON = ContextVar("brapi_fallback_reason", default="explicit_provider_request")


class BrapiBudgetExceeded(RuntimeError):
    pass


@contextmanager
def fallback_reason(reason: str):
    token = _REASON.set(reason[:500])
    try:
        yield
    finally:
        _REASON.reset(token)


class BrapiBudget:
    def __init__(self, path: Path | None = None):
        configured = os.getenv("B3_BRAPI_BUDGET_PATH")
        self.path = path or (Path(configured) if configured else settings.data_dir / "providers" / "brapi_budget.sqlite3")

    def _period(self, now: datetime) -> str:
        local = now.astimezone(ZoneInfo(os.getenv("B3_BRAPI_BILLING_TIMEZONE", "America/Sao_Paulo")))
        day = int(os.getenv("B3_BRAPI_BILLING_DAY", "1"))
        if not 1 <= day <= 28:
            raise ValueError("B3_BRAPI_BILLING_DAY must be 1..28")
        year, month = local.year, local.month
        if local.day < day:
            month -= 1
            if not month:
                year, month = year - 1, 12
        return f"{year:04d}-{month:02d}-{day:02d}"

    def _limits(self, period: str) -> tuple[int, int]:
        # Baselines are period-specific; never silently carry last month's
        # account reconciliation into a new billing period.
        baseline = (int(os.getenv("B3_BRAPI_BASELINE_USED", "0"))
                    if os.getenv("B3_BRAPI_BASELINE_PERIOD") == period else 0)
        allowance = int(os.getenv("B3_BRAPI_LOCAL_ALLOWANCE", "0"))
        reserve = int(os.getenv("B3_BRAPI_OPERATIONAL_RESERVE", "100"))
        if min(baseline, allowance, reserve) < 0:
            raise ValueError("BRAPI budget values must be nonnegative")
        return min(allowance, max(0, 15000 - baseline - reserve)), baseline

    @contextmanager
    def _connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=30)
        connection.execute("CREATE TABLE IF NOT EXISTS periods (period TEXT PRIMARY KEY, used INTEGER NOT NULL)")
        connection.execute("CREATE TABLE IF NOT EXISTS attempts (period TEXT, reserved_at TEXT, endpoint TEXT, reason TEXT)")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def reserve(self, url: str, *, now: datetime | None = None) -> None:
        instant = now or datetime.now(timezone.utc)
        period = self._period(instant)
        ceiling, _ = self._limits(period)
        # Keep paths only. Queries and headers may contain credentials.
        endpoint = urlsplit(url).path[:200]
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("INSERT OR IGNORE INTO periods VALUES (?, 0)", (period,))
            used = connection.execute("SELECT used FROM periods WHERE period=?", (period,)).fetchone()[0]
            if used >= ceiling:
                raise BrapiBudgetExceeded("BRAPI local allowance exhausted or not configured; request blocked before HTTP")
            connection.execute("UPDATE periods SET used=used+1 WHERE period=?", (period,))
            connection.execute("INSERT INTO attempts VALUES (?, ?, ?, ?)", (period, instant.isoformat(), endpoint, _REASON.get()))

    def snapshot(self, *, now: datetime | None = None) -> dict:
        period = self._period(now or datetime.now(timezone.utc))
        ceiling, baseline = self._limits(period)
        with self._connect() as connection:
            row = connection.execute("SELECT used FROM periods WHERE period=?", (period,)).fetchone()
        used = row[0] if row else 0
        return {"period": period, "monthly_hard_limit": 15000, "local_ceiling": ceiling,
                "local_attempts": used, "local_remaining": max(0, ceiling-used),
                "baseline_used": baseline, "account_balance_verified": False,
                "status": "BLOCKED" if used >= ceiling else "AVAILABLE",
                "usage_fraction": used / ceiling if ceiling else None}


def budgeted_urlopen(request, *, timeout, opener):
    BrapiBudget().reserve(request.full_url)
    return opener(request, timeout=timeout)
