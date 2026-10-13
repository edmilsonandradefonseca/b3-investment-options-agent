#!/usr/bin/env python3
"""Run real B3 workspace requests against the colocated runtime.

Full request/response bodies are written only to a mode-0600 file under the
runner user's home directory. Console output is intentionally metadata-only
because this repository is public and responses may contain personal portfolio
context. No artifact is uploaded by the companion workflow.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_TIMEOUT_SECONDS = 210
MAX_RESPONSE_BYTES = 20 * 1024 * 1024


def make_cases() -> list[dict[str, Any]]:
    common = {
        "research_mode": "stored_first",
        "option_filter": None,
        "horizon": "1M",
    }
    return [
        {
            "id": "opportunities_petr4",
            "label": "Opportunities / PETR4",
            "request": {
                "task": "Analise PETR4 em Opportunities como oportunidade dentro e fora da carteira. Compare manter a posição atual, comprar a ação e alternativas canônicas disponíveis, incluindo opções apenas se houver cadeia válida. Mostre os candidatos realmente calculados, preço e horário, retorno/risco e liquidez somente quando disponíveis, capital exigido, impacto na carteira, custo de oportunidade e critérios de ranking. Explique evidências favoráveis e contrárias, riscos, fontes, as_of e dados faltantes. Separe fatos determinísticos de hipóteses qualitativas; não invente candidatos, preços, probabilidades ou recomendação de compra/venda.",
                "ticker": "PETR4",
                "context": {
                    **common,
                    "workspace": "Opportunities",
                    "selected_ticker": "PETR4",
                    "asset_view": False,
                },
            },
        },
        {
            "id": "market_intelligence_vale3",
            "label": "Market Intelligence / VALE3",
            "request": {
                "task": "Faça uma análise de Market Intelligence de VALE3. Apresente cotação e horário, gráfico/série histórica e volume para os períodos disponíveis, tendência e indicadores técnicos determinísticos, fundamentos e estimativas apenas com fonte e data, regime de mercado e fatores relevantes (minério de ferro, China, dólar, juros e fluxo) quando houver dados. Resuma notícias/eventos com publicação, fonte, impacto potencial, evidência favorável e contrária; inclua riscos, cenários qualitativos, conclusão proporcional à qualidade da evidência e lacunas. UC-05/06/10: diferencie fatos canônicos, pesquisa armazenada/atualizada e inferência; preserve as_of e proveniência; declare UNKNOWN quando faltar dado. Não invente números, consenso ou notícias.",
                "ticker": "VALE3",
                "context": {
                    **common,
                    "workspace": "Market Intelligence",
                    "selected_ticker": "VALE3",
                    "asset_view": True,
                },
            },
        },
        {
            "id": "strategy_lab_stock_buy_comparison",
            "label": "Strategy Lab / ITUB4 BUY × BBDC4 BUY",
            "request": {
                "task": "No Strategy Lab, compare duas alternativas equivalentes: comprar ações ITUB4 versus comprar ações BBDC4, sem opções e sem executar ordens. Para cada uma mostre cotação atual e horário, capital por ação e para uma mesma quantidade/orçamento somente se disponível, histórico e retorno nos períodos suportados, risco/volatilidade e drawdown determinísticos, liquidez, fundamentos e eventos com data/fonte. Compare lado a lado retorno, risco, concentração/setor e impacto na minha carteira, dividendos se houver informação canônica, cenários explícitos sem atribuir probabilidades não calculadas, custo de oportunidade, premissas, evidência a favor/contra e dados ausentes. Indique qual métrica permite ou impede ordenar as alternativas; não declare vencedor se os dados ou política determinística não sustentarem. UC-04: separe fatos, cenários e interpretação, preserve as_of e proveniência; não invente números.",
                "ticker": None,
                "context": {
                    **common,
                    "workspace": "Strategy Lab",
                    "selected_ticker": None,
                    "asset_view": False,
                    "comparison_assets": ["ITUB4", "BBDC4"],
                    "strategy_a": "Comprar ação",
                    "strategy_b": "Comprar ação",
                    "option_a": None,
                    "option_b": None,
                    "comparison_amount": None,
                    "scenario_horizon": None,
                    "scenario_shocks_pct": None,
                    "scenario_objective": "COMPARE_ONLY",
                },
            },
        },
        {
            "id": "copilot_natural_language_compare",
            "label": "Copilot / comparar ITUB4 versus BBDC4",
            "request": {
                "task": "Compare comprar ações ITUB4 e comprar ações BBDC4. Use dados atuais e históricos disponíveis, risco, valuation/fundamentos, dividendos e efeito na minha carteira; mostre valores, datas e fontes e explicite o que estiver indisponível. Não invente dados nem force um vencedor.",
                "ticker": "PETR4",
                "context": {
                    **common,
                    "workspace": "Market Intelligence",
                    "selected_ticker": "PETR4",
                    "asset_view": False,
                },
            },
        },
    ]


def read_json_body(raw: bytes) -> Any:
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"_raw_text": raw.decode("utf-8", errors="replace")}


def call_json(url: str, payload: dict[str, Any] | None, timeout: float) -> dict[str, Any]:
    headers = {"Accept": "application/json"}
    data = None
    method = "GET"
    if payload is not None:
        method = "POST"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=headers, method=method)
    started = time.monotonic()
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            status = int(response.status)
    except HTTPError as exc:
        status = int(exc.code)
        raw = exc.read(MAX_RESPONSE_BYTES + 1)
    except (URLError, TimeoutError, OSError) as exc:
        elapsed_ms = round((time.monotonic() - started) * 1000, 1)
        reason = getattr(exc, "reason", None)
        return {
            "http_status": None,
            "elapsed_ms": elapsed_ms,
            "response_bytes": 0,
            "transport_error_type": type(reason if reason is not None else exc).__name__,
            "response": None,
        }
    elapsed_ms = round((time.monotonic() - started) * 1000, 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        return {
            "http_status": status,
            "elapsed_ms": elapsed_ms,
            "response_bytes": len(raw),
            "transport_error_type": "RESPONSE_TOO_LARGE",
            "response": None,
        }
    return {
        "http_status": status,
        "elapsed_ms": elapsed_ms,
        "response_bytes": len(raw),
        "transport_error_type": None,
        "response": read_json_body(raw),
    }


def response_metadata(response: Any) -> dict[str, Any]:
    if not isinstance(response, dict):
        return {"payload_type": type(response).__name__}
    result = response.get("result")
    result = result if isinstance(result, dict) else {}
    telemetry = result.get("telemetry")
    telemetry = telemetry if isinstance(telemetry, dict) else {}
    return {
        "api_status": response.get("status"),
        "result_keys": sorted(str(key) for key in result.keys())[:80],
        "source_count": len(response.get("sources", [])) if isinstance(response.get("sources"), list) else None,
        "derived_synthesis_status": result.get("derived_synthesis_status"),
        "telemetry_total_ms": telemetry.get("total_ms"),
        "telemetry_llm_calls": telemetry.get("llm_calls"),
        "api_error_present": bool(response.get("error")),
    }


def write_private_report(report_dir: Path, report: dict[str, Any]) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        report_dir.chmod(0o700)
    except OSError:
        pass
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = report_dir / f"b3-live-workspaces-{stamp}.json"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(path, flags, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("B3_BASE_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument(
        "--report-dir",
        default=os.getenv(
            "B3_REPORT_DIR",
            str(Path.home() / ".local/share/b3-investment-options-agent/live-validation"),
        ),
    )
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")
    report: dict[str, Any] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "timeout_seconds_per_request": args.timeout_seconds,
        "privacy": "Full HTTP responses are stored locally with mode 0600; console output contains metadata only.",
        "health": call_json(f"{base_url}/health", None, min(args.timeout_seconds, 15)),
        "cases": [],
    }
    health = report["health"]
    failures = int(health["http_status"] != 200 or health["transport_error_type"] is not None)
    print(f"HEALTH http={health['http_status']} elapsed_ms={health['elapsed_ms']} transport_error={health['transport_error_type']}", flush=True)
    for case in make_cases():
        result = call_json(
            f"{base_url}/orchestrate",
            case["request"],
            args.timeout_seconds,
        )
        entry = {
            "id": case["id"],
            "label": case["label"],
            "request": case["request"],
            **result,
            "response_metadata": response_metadata(result.get("response")),
        }
        report["cases"].append(entry)
        metadata = entry["response_metadata"]
        failed = (
            result["http_status"] != 200
            or result["transport_error_type"] is not None
            or metadata.get("api_error_present") is True
        )
        failures += int(failed)
        print(
            f"CASE {case['id']} http={result['http_status']} "
            f"elapsed_ms={result['elapsed_ms']} bytes={result['response_bytes']} "
            f"api_status={metadata.get('api_status')} "
            f"source_count={metadata.get('source_count')} "
            f"derived_synthesis={metadata.get('derived_synthesis_status')} "
            f"transport_error={result['transport_error_type']} failed={failed}",
            flush=True,
        )
    path = write_private_report(Path(args.report_dir).expanduser(), report)
    report["validation_failure_count"] = failures
    print(f"PRIVATE_REPORT={path}", flush=True)
    print("REPORT_CONTENT=not printed; no response body or portfolio data is sent to Actions logs.", flush=True)
    print(f"VALIDATION_FAILURE_COUNT={failures}", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
