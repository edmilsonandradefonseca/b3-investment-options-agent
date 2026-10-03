#!/usr/bin/env python3
"""Validate the candidate app instance with Ubuntu's actual runtime inputs.

No model calls, fixtures, new ledgers or response bodies in Actions logs.
This is an isolated ASGI instance, not proof that systemd loaded the new code.
"""
from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
from time import monotonic


def main() -> int:
    pid = subprocess.check_output(
        ["systemctl", "show", "b3-runtime.service", "--property=MainPID", "--value"],
        text=True, timeout=10,
    ).strip()
    if not pid.isdecimal() or int(pid) <= 0:
        raise RuntimeError("Runtime service has no active process")
    # Copy only this application's provider/configuration keys; never print values.
    raw = Path(f"/proc/{pid}/environ").read_bytes()
    for field in raw.split(b"\0"):
        key, sep, value = field.partition(b"=")
        name = key.decode("utf-8", errors="strict")
        if sep and (name.startswith("B3_") or name in {"OPLAB_API_TOKEN", "BRAPI_TOKEN"}):
            os.environ[name] = value.decode("utf-8", errors="strict")
    os.environ["B3_AGENT_DATA_DIR"] = "/opt/b3-runtime/data"
    os.environ["B3_AGENT_PROJECT_ROOT"] = str(Path(__file__).resolve().parents[1])
    from fastapi.testclient import TestClient
    from b3_agent.server import app

    client = TestClient(app)
    started = monotonic()
    data = client.get("/analysis/live/PETR4").json()
    bars = data["market"]["price_history"]
    cutoff = datetime.fromisoformat(data["as_of"].replace("Z", "+00:00"))
    assert len(bars) == data["market"]["history_count"] >= 85
    for bar in bars:
        for key in ("observation_timestamp", "available_timestamp"):
            assert datetime.fromisoformat(bar[key].replace("Z", "+00:00")) <= cutoff
    assert data["options"]["contract_count"] == 0
    assert data["market"]["quant"]["data_points"] == len(bars)
    print(json.dumps({"case": "PETR4_chart_contract", "status": "PASS", "bars": len(bars), "elapsed_ms": round((monotonic()-started)*1000, 1)}), flush=True)
    cases = [
        ("Opportunities", "PETR4", {}),
        ("Strategy Lab", None, {"comparison_assets": ["ITUB4", "BBDC4"], "strategy_a": "Comprar ação", "strategy_b": "Comprar ação"}),
    ]
    for workspace, ticker, extra in cases:
        started = monotonic()
        response = client.post("/orchestrate", json={
            "task": "UC-03 analise PETR4" if ticker else "UC-04 compare ITUB4 e BBDC4",
            "ticker": ticker,
            "context": {"workspace": workspace, "selected_ticker": ticker, "analysis_mode": "deterministic", "research_mode": "stored_only", **extra},
        })
        assert response.status_code == 200
        data = response.json()
        assert not data["error"]
        result = data["result"]
        assert result["workspace_intelligence"]["workspace"] == workspace
        assert result["derived_synthesis_status"] == "NOT_REQUESTED"
        assert result["telemetry"]["llm_calls"] == 0
        count = None
        if ticker:
            assert "opportunity_set" in result and "opportunity_ranking_status" in result
            count = len(result["opportunity_set"]["ranked_opportunities"])
        else:
            assert len(result["strategy_comparison"]["alternatives"]) == 2
            assert set(result["asset_evidence"]) == {"ITUB4", "BBDC4"}
        print(json.dumps({"case": workspace, "status": "PASS", "elapsed_ms": round((monotonic()-started)*1000, 1), "candidate_count": count, "ranking_status": result.get("opportunity_ranking_status"), "llm_calls": 0}), flush=True)
    print("INSTANCE=isolated ASGI app using actual Ubuntu provider configuration and runtime data", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
