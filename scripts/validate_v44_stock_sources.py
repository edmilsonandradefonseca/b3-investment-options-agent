"""Candidate source/API acceptance using isolated caches and zero BRAPI allowance.

Does not restart the service, write portfolio state, or print raw responses.
"""
import json
import os
from pathlib import Path
import subprocess
import tempfile
from time import monotonic

pid = subprocess.check_output(["systemctl", "show", "b3-runtime.service", "--property=MainPID", "--value"], text=True, timeout=10).strip()
assert pid.isdecimal() and int(pid) > 0
for field in Path(f"/proc/{pid}/environ").read_bytes().split(b"\0"):
    key, sep, value = field.partition(b"=")
    name = key.decode("utf-8")
    if sep and (name.startswith("B3_") or name in {"OPLAB_API_TOKEN", "BRAPI_TOKEN"}):
        os.environ[name] = value.decode("utf-8")

with tempfile.TemporaryDirectory(prefix="b3-v44-sources-") as directory:
    root = Path(directory)
    (root / "archive").symlink_to(Path("/opt/b3-runtime/data/archive"), target_is_directory=True)
    os.environ["B3_AGENT_PROJECT_ROOT"] = str(Path(__file__).resolve().parents[1])
    os.environ["B3_AGENT_DATA_DIR"] = str(root)
    os.environ["B3_BRAPI_BUDGET_PATH"] = str(root / "quota.sqlite3")
    os.environ["B3_BRAPI_LOCAL_ALLOWANCE"] = "0"
    from fastapi.testclient import TestClient
    from b3_agent.server import app
    from b3_agent.providers.stock_sources import StockQuoteProvider
    from b3_agent.providers.brapi.budget import BrapiBudget
    client = TestClient(app)
    failures = []
    for ticker in ("PETR4", "ITUB4", "BBDC4", "VALE3"):
        start = monotonic()
        response = client.get(f"/analysis/live/{ticker}")
        body = response.json()
        history = body.get("market", {}).get("price_history", [])
        print(json.dumps({"case": "candidate history API", "ticker": ticker, "http": response.status_code,
            "rows": len(history), "sources": sorted({r["source"] for r in history}),
            "elapsed_s": round(monotonic()-start, 2), "active_service_changed": False}), flush=True)
        if response.status_code != 200 or not history:
            failures.append(f"history:{ticker}")
        start = monotonic()
        response = client.get(f"/fundamentals/{ticker}")
        body = response.json()
        metrics = body.get("metrics", [])
        print(json.dumps({"case": "candidate fundamentals API", "ticker": ticker, "http": response.status_code,
            "metrics": len(metrics), "sources": sorted({r["source"] for r in metrics}),
            "units": sorted({r["unit"] for r in metrics if r.get("unit")}),
            "diagnostics": body.get("provider_diagnostics", []), "elapsed_s": round(monotonic()-start, 2)}), flush=True)
        if response.status_code != 200 or not metrics:
            failures.append(f"fundamentals:{ticker}")
    provider = StockQuoteProvider()
    start = monotonic()
    try:
        quote = provider.get_current_quote("PETR4")
        print(json.dumps({"case": "candidate current quote", "source": quote.source,
            "observed_at": quote.observation_timestamp.isoformat(), "flags": quote.quality_flags,
            "elapsed_s": round(monotonic()-start, 2), "telemetry": provider.last_reuse_telemetry}), flush=True)
    except (RuntimeError, OSError, ValueError) as exc:
        failures.append("current_quote:PETR4")
        print(json.dumps({"case":"candidate current quote", "error_type": type(exc).__name__,
            "elapsed_s":round(monotonic()-start,2), "telemetry":provider.last_reuse_telemetry}), flush=True)
    quota = BrapiBudget().snapshot()
    assert quota["local_attempts"] == 0, "Acceptance must not spend any BRAPI request"
    print(json.dumps({"case": "candidate quota", **quota}), flush=True)
    assert not failures, "Candidate source gaps: " + ", ".join(failures)
    print("PASS WS-03/06: candidate real stock sources and APIs; BRAPI blocked before HTTP", flush=True)
