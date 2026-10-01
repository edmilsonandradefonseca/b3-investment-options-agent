"""Read projections over existing execution truth; no migrations or duplicate ledger.

Retrospective executions are NOT complete economic operations or PIT experiences.
Unknown starting balances, assignment, coverage, fees and rolls stay unknown.
"""
from collections import Counter, defaultdict
from contextlib import closing
from datetime import date, datetime, time, timezone
from decimal import Decimal
from pathlib import Path
import math
import sqlite3
from time import monotonic
from zoneinfo import ZoneInfo

from b3_agent.historical_operations import HistoricalOperationsService
from b3_agent.schemas.transaction import Transaction
from b3_agent.intelligence.reuse import ContextReuse, fingerprint

_SOURCE_CACHE = ContextReuse(capacity=16, ttl_seconds=30)
ZONE = ZoneInfo("America/Sao_Paulo")
LIMIT = 50000


def _read(path, table, columns):
    if not path.is_file():
        return [], "MISSING", False
    with closing(sqlite3.connect(path.resolve().as_uri()+"?mode=ro", uri=True, timeout=2)) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
        deadline = monotonic() + 3
        conn.set_progress_handler(lambda: int(monotonic() > deadline), 1000)
        conn.execute("BEGIN")
        existing = {r[1] for r in conn.execute(f'PRAGMA table_info("{table}")')}
        if not existing:
            return [], "TABLE_MISSING", False
        selected = [c for c in columns if c in existing]
        if not selected:
            return [], "SCHEMA_UNSUPPORTED", False
        rows = conn.execute(f'SELECT {",".join(selected)} FROM "{table}" LIMIT ?', (LIMIT+1,)).fetchall()
        return [dict(row) for row in rows[:LIMIT]], "READ_OK", len(rows)>LIMIT


def _revision(data_dir):
    values = []
    for name in ("options.sqlite3", "b3_agent.db", "source_manifest.sqlite3"):
        for suffix in ("", "-wal"):
            path = data_dir / (name+suffix)
            try:
                s = path.stat()
                values.append((str(path), s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns))
            except FileNotFoundError:
                values.append((str(path), None))
    return values


def _utc(value):
    result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timezone missing")
    return result.astimezone(timezone.utc)


class PersonalHistoryService:
    """Bounded current retrospective context, or strict known-at-time replay."""
    def __init__(self, data_dir):
        self.data_dir = Path(data_dir).resolve()

    def build(self, *, ticker=None, as_of=None, since=None):
        started = monotonic()
        strict_pit = as_of is not None
        cutoff = _utc(as_of) if as_of is not None else datetime.now(timezone.utc)
        since_date = date.fromisoformat(str(since)) if since is not None else None
        selected = ticker.strip().upper() if ticker else None
        warnings = [
            "Coverage and opening balances are UNKNOWN; cash flows are not total investment profit.",
            "Assignment, exercise, expiry, rolls and covered-call state are UNKNOWN without independent evidence.",
            "No entry IV/regime snapshots: no validated similarity, active learning or predictive probability is inferred.",
            "Personal execution observations are not market probabilities.",
        ]
        revision = None
        try:
            revision = _revision(self.data_dir)
            def read_sources():
                sources = {}
                for name, table, columns in (
                    ("options.sqlite3", "option_transactions", "transaction_id option_ticker broker quantity average_cost total_cost as_of source_ref source_type source_id note_number"),
                    ("b3_agent.db", "transactions", "transaction_id executed_at action instrument_type ticker quantity price broker source_ref"),
                    ("source_manifest.sqlite3", "source_manifest", "source_id source_type imported_at coverage_start coverage_end completeness source_ref"),
                ):
                    rows, status, truncated = _read(self.data_dir/name, table, columns.split())
                    sources[table] = {"rows": rows, "status": status, "truncated": truncated}
                if _revision(self.data_dir) != revision:
                    raise RuntimeError("SOURCE_CHANGED_DURING_READ")
                return sources
            sources, reuse = _SOURCE_CACHE.get_or_build(fingerprint(["history-read-v1", revision]), read_sources)
        except (OSError, sqlite3.Error, RuntimeError) as exc:
            return {"status": "UNAVAILABLE", "coverage": "UNKNOWN", "as_of": cutoff.isoformat(), "limitations": warnings+[f"Read failed: {type(exc).__name__}"], "executions": [], "assignment_frequency": None, "telemetry": {"total_ms": (monotonic()-started)*1000, "cache": "ERROR"}}
        excluded = Counter()
        manifest = defaultdict(list)
        for row in sources["source_manifest"]["rows"]:
            if row.get("source_type") == "BROKERAGE_NOTE":
                try:
                    manifest[str(row.get("source_id"))].append(_utc(row["imported_at"]))
                except (KeyError, ValueError, TypeError):
                    pass
        executions = []
        identities = set()
        for table in ("option_transactions", "transactions"):
            for row in sources[table]["rows"]:
                try:
                    option = table == "option_transactions"
                    symbol = str(row["option_ticker" if option else "ticker"]).upper().strip()
                    broker = str(row.get("broker") or "").strip()
                    qty = float(row["quantity"])
                    price = float(row["average_cost" if option else "price"])
                    if not math.isfinite(qty) or not math.isfinite(price) or qty == 0 or price < 0:
                        raise ValueError("invalid economics")
                    side = ("BUY" if qty > 0 else "SELL") if option else row["action"]
                    if side not in {"BUY", "SELL"} or (not option and qty < 0):
                        raise ValueError("invalid side")
                    kind = "OPTION" if option else row["instrument_type"]
                    if kind not in {"STOCK", "OPTION"}:
                        raise ValueError("unsupported instrument")
                    ref = str(row.get("source_ref") or "")
                    if option and row.get("source_type") != "BROKERAGE_NOTE" and not ref.startswith("BTG:NotaCorretagem:"):
                        excluded["NOT_EXECUTION_PROVENANCE"] += 1
                        continue
                    raw_time = str(row["as_of" if option else "executed_at"])
                    date_only = len(raw_time) == 10
                    # Sort date-only notes conservatively at end of local day;
                    # this is explicitly NOT an observed execution timestamp.
                    stamp = datetime.combine(date.fromisoformat(raw_time), time.max, ZONE).astimezone(timezone.utc) if date_only else _utc(raw_time)
                    after_cutoff = stamp > cutoff if (strict_pit or not date_only) else stamp.astimezone(ZONE).date() > cutoff.astimezone(ZONE).date()
                    if after_cutoff:
                        excluded["AFTER_AS_OF"] += 1
                        continue
                    if strict_pit:
                        available = manifest.get(str(row.get("source_id") or row.get("note_number")), []) if option else []
                        # No ingestion/available timestamp in manual transactions.
                        if not available or min(available) > cutoff:
                            excluded["AVAILABILITY_NOT_PROVEN_AT_AS_OF"] += 1
                            continue
                    if since_date and stamp.astimezone(ZONE).date() < since_date:
                        # Preserve earlier rows for reconstruction; presentation filters later.
                        in_window = False
                    else:
                        in_window = True
                    identity = "EXACT_SYMBOL" if not selected or symbol == selected else "UNVERIFIED_OPTION_ROOT" if kind == "OPTION" and len(selected) >= 5 and symbol[:4] == selected[:4] else None
                    if identity is None:
                        continue
                    amount = Decimal(str(abs(qty))) * Decimal(str(price))
                    cash = amount if side == "SELL" else -amount
                    if option and row.get("total_cost") is not None:
                        total = Decimal(str(row["total_cost"]))
                        if not total.is_finite() or abs(total+cash)>Decimal("0.011"):
                            excluded["AMOUNT_MISMATCH"] += 1
                            continue
                    economic_key = (symbol, broker, stamp.astimezone(ZONE).date(), side, abs(qty), price)
                    if not option and economic_key in identities:
                        excluded["POSSIBLE_CROSS_LEDGER_DUPLICATE"] += 1
                        continue
                    if option:
                        identities.add(economic_key)
                    executions.append({"transaction_id": str(row["transaction_id"]), "source_table": table, "symbol": symbol, "broker": broker, "instrument_type": kind, "side": side, "quantity": abs(qty), "price": price, "cash_flow": float(cash), "trade_date": stamp.astimezone(ZONE).date().isoformat(), "execution_timestamp": None if date_only else stamp.isoformat(), "date_precision": "DAY" if date_only else "TIMESTAMP", "source_ref": ref, "identity_match": identity, "in_window": in_window, "_sort_time": stamp})
                except (KeyError, ValueError, TypeError, ArithmeticError):
                    excluded["INVALID_ROW"] += 1
        executions.sort(key=lambda row: (row["_sort_time"], row["transaction_id"]))
        groups = defaultdict(list)
        for item in executions:
            groups[(item["broker"], item["symbol"])].append(item)
        cycles = []
        for (broker, symbol), rows in groups.items():
            # An account-less broker label is not proof of full account coverage.
            if not broker:
                excluded["BROKER_IDENTITY_UNKNOWN"] += len(rows)
                continue
            if len({r["transaction_id"] for r in rows}) != len(rows):
                excluded["DUPLICATE_TRANSACTION_ID"] += len(rows)
                continue
            day_sides = defaultdict(set)
            for row in rows:
                day_sides[row["trade_date"]].add(row["side"])
            if any(r["date_precision"] == "DAY" and len(day_sides[r["trade_date"]]) > 1 for r in rows):
                excluded["INTRADAY_ORDER_UNKNOWN"] += len(rows)
                continue
            try:
                txs = [Transaction(transaction_id=r["transaction_id"], executed_at=r["_sort_time"], action=r["side"], instrument_type=r["instrument_type"], ticker=r["symbol"], quantity=r["quantity"], price=r["price"], broker=broker, source_ref=r["source_ref"]) for r in rows]
                reconstructed = HistoricalOperationsService().build(txs)
                for op in reconstructed.closed_operations:
                    ids = set(op.source_transaction_ids)
                    members = [r for r in rows if r["transaction_id"] in ids]
                    if not any(r["in_window"] for r in members):
                        continue
                    cycles.append({"operation_id": op.operation_id, "symbol": symbol, "broker": broker, "status": "OBSERVED_NET_FLAT_SEQUENCE", "economic_outcome_status": "UNKNOWN", "gross_execution_cash_flow": float(sum(Decimal(str(r["cash_flow"])) for r in members)), "source_transaction_ids": list(op.source_transaction_ids), "source_refs": list(op.source_refs), "opening_balance_assumption": "ZERO_UNVERIFIED", "eligible_for_learning": False})
            except ValueError:
                excluded["RECONSTRUCTION_AMBIGUOUS"] += len(rows)
        visible = [{k:v for k,v in r.items() if k not in {"_sort_time", "in_window"}} for r in executions if r["in_window"]]
        fp = fingerprint(["personal-history-v1", str(self.data_dir), sources, selected, str(since), cutoff.isoformat() if strict_pit else "RETROSPECTIVE"])
        return {
            "status": "LIMITED" if visible else "NO_MATCHING_EXECUTIONS",
            "authority": "existing_sqlite_execution_projection", "coverage": "UNKNOWN",
            "as_of": cutoff.isoformat(), "since": str(since) if since else None,
            "mode": "STRICT_KNOWN_AT_TIME" if strict_pit else "RETROSPECTIVE_AS_LOADED",
            "ticker": selected, "fingerprint": fp,
            "sources": {k:{"status":v["status"], "loaded_row_count":len(v["rows"]), "truncated":v["truncated"]} for k,v in sources.items()},
            "execution_count": len(visible), "executions": visible[-20:], "execution_details_omitted": max(0,len(visible)-20),
            "cash_flow_observed": float(sum(Decimal(str(r["cash_flow"])) for r in visible)) if visible else None,
            "net_flat_sequence_count": len(cycles), "net_flat_sequences": cycles[-10:],
            "assignment_frequency": None, "expiry_frequency": None, "roll_frequency": None,
            "learning_sample_size": 0, "validated_similarity": None,
            "excluded": dict(excluded), "source_refs": sorted({r["source_ref"] for r in visible[-20:] if r["source_ref"]}),
            "limitations": warnings + (["Input rows truncated; no complete-period statistics are available."] if any(v["truncated"] for v in sources.values()) else []),
            "telemetry": {**reuse, "total_ms": (monotonic()-started)*1000},
        }
