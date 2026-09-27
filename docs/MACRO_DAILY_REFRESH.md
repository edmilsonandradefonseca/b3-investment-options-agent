# B3 Macro Daily Refresh

## Policy

The B3 backend refreshes structured macro data from Banco Central do Brasil
SGS on Brazilian weekdays at **19:00 America/Sao_Paulo**.

Current core series:

- SELIC — SGS 1178
- CDI — SGS 12
- IPCA — SGS 433

The scheduled job fetches a rolling 120-day window so delayed publication of
monthly IPCA is discovered automatically while daily SELIC/CDI observations are
kept current.

## Persistence

Normalized records are stored in:

```text
data/normalized/macro/macro.parquet
```

Persistence is idempotent by provider `source_record_id`.

If the same observation is fetched again, the existing record is retained.
This preserves the earliest availability timestamp already observed by the B3
runtime and avoids rewriting point-in-time history.

## Manual execution

```bash
cd /opt/b3-investment-options-agent
.venv/bin/python scripts/update_macro.py
```

Expected output:

```text
MACRO REFRESH OK window=... fetched=... inserted=... duplicates=... CDI=... IPCA=... SELIC=...
```

A second execution on the same day should normally report mostly or entirely
duplicates rather than creating duplicate rows.

## Install the production timer

```bash
cd /opt/b3-investment-options-agent
bash scripts/install_macro_refresh_timer.sh
```

The installer creates:

- `b3-macro-refresh.service`
- `b3-macro-refresh.timer`

The timer is persistent, so a missed scheduled execution can run after the host
comes back online.

## Operations

Check the next execution:

```bash
systemctl list-timers b3-macro-refresh.timer --no-pager
```

Run immediately:

```bash
sudo systemctl start b3-macro-refresh.service
```

Inspect the last run:

```bash
systemctl status b3-macro-refresh.service --no-pager
journalctl -u b3-macro-refresh.service -n 100 --no-pager
```

This job belongs to the B3 application. It does not start, stop, restart, or
reconfigure shared Qdrant, Neo4j, embedding, or SearXNG services.
