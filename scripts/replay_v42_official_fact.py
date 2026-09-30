#!/usr/bin/env python3
"""Replay one real historical CVM Fato Relevante through DeepSeek and OpenClaw.

This is the V4.2 reasoning acceptance track. It never fabricates an event:
the selected evidence must come from CVM Open Data IPE and must have been
classified MATERIAL by the deterministic OFFICIAL_FATO_RELEVANTE rule.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from b3_agent.config import settings
from b3_agent.intelligence.issuer_registry import IssuerRegistry
from b3_agent.intelligence.official_evidence import (
    OfficialEvidenceBuilder,
    evidence_for_reasoning,
    evidence_to_dict,
)
from b3_agent.knowledge.evidence import Evidence
from b3_agent.llm.client import OpenClawStructuredClient
from b3_agent.llm.ollama_client import OllamaClient
from b3_agent.llm.ollama_runtime import ollama_preflight
from b3_agent.providers.cvm_open_data import CvmOpenDataProvider


SENIOR_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "risks": {"type": "array", "items": {"type": "string"}},
        "catalysts": {"type": "array", "items": {"type": "string"}},
        "contradictions": {"type": "array", "items": {"type": "string"}},
        "limitations": {"type": "array", "items": {"type": "string"}},
        "evidence_refs": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "summary",
        "risks",
        "catalysts",
        "contradictions",
        "limitations",
        "evidence_refs",
    ],
    "additionalProperties": False,
}


def select_material_evidence(
    evidences: tuple[Evidence, ...],
    *,
    protocol: str | None = None,
) -> Evidence:
    selected = [
        item
        for item in evidences
        if item.metadata.materiality == "MATERIAL"
        and item.metadata.materiality_reason == "OFFICIAL_FATO_RELEVANTE"
        and (
            protocol is None
            or str(item.metadata.extra.get("protocol") or "") == protocol
        )
    ]
    if not selected:
        raise RuntimeError("no real CVM Fato Relevante matched the replay criteria")

    def key(item: Evidence):
        return (
            item.metadata.published_at
            or item.metadata.reference_at
            or item.metadata.retrieved_at
        )

    return max(selected, key=key)


def replay_prompt(ticker: str, evidence: Evidence) -> str:
    payload = evidence_for_reasoning(evidence)
    return (
        "Historical V4.2 replay. Analyze only the supplied canonical CVM evidence. "
        "This is not a current-market claim and not an investment recommendation. "
        "Do not invent prices, causes, probabilities or facts absent from evidence. "
        "Produce a concise dossier of at most 220 words. Sections: Evidence summary; "
        "Risks; Catalysts; Contradictions; Limitations. Explicitly preserve the "
        "historical/PIT limitation and UNKNOWN values. "
        f"Ticker: {ticker}\nCanonical Evidence JSON:\n"
        + json.dumps(payload, ensure_ascii=False)
    )


def save_artifact(root: Path, artifact: dict) -> None:
    root.mkdir(parents=True, exist_ok=True)
    runs = root / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_path = runs / f"{artifact['ticker']}_{artifact['year']}_{stamp}.json"
    run_path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    latest = root / "latest.json"
    temp = latest.with_suffix(".tmp")
    temp.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    temp.replace(latest)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="PETR4")
    parser.add_argument("--year", type=int, default=datetime.now(timezone.utc).year)
    parser.add_argument("--protocol")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="select and validate real official evidence without calling DeepSeek/OpenClaw",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=settings.data_dir / "derived" / "v42_historical_replay",
    )
    args = parser.parse_args()

    ticker = args.ticker.upper().strip()
    provider = CvmOpenDataProvider()
    registry = IssuerRegistry()
    started_at = datetime.now(timezone.utc)
    stage = "registry_sync"

    try:
        registry_sync = registry.sync_from_cvm(provider=provider, year=args.year)
        stage = "issuer_resolution"
        issuer = registry.resolve_issuer_by_ticker(ticker)
        if issuer is None:
            raise RuntimeError(f"issuer registry did not resolve {ticker}")

        stage = "official_evidence_acquisition"
        ipe = provider.fetch_ipe_year(
            args.year,
            cvm_codes=(issuer.cvm_code,) if issuer.cvm_code else (),
            cnpjs=(issuer.cnpj,) if issuer.cnpj else (),
            categories=("Fato Relevante",),
        )
        stage = "official_evidence_normalization"
        builder = OfficialEvidenceBuilder(registry=registry)
        evidences = tuple(
            builder.from_open_data_ipe(record)
            for record in ipe.records
        )
        stage = "material_evidence_selection"
        evidence = select_material_evidence(
            evidences,
            protocol=args.protocol,
        )
        if ticker not in evidence.metadata.ticker_refs:
            raise RuntimeError(
                f"selected official evidence is not mapped to requested ticker {ticker}"
            )

        evidence_ref = evidence.source_url or evidence.evidence_id

        reasoning_evidence = evidence_for_reasoning(evidence)
        prompt = replay_prompt(ticker, evidence)

        if args.dry_run:
            print(
                json.dumps(
                    {
                        "status": "READY",
                        "ticker": ticker,
                        "year": args.year,
                        "issuer": {
                            "issuer_id": issuer.issuer_id,
                            "cvm_code": issuer.cvm_code,
                            "cnpj": issuer.cnpj,
                            "legal_name": issuer.legal_name,
                        },
                        "selected_evidence": {
                            "evidence_id": evidence.evidence_id,
                            "title": evidence.title,
                            "source_url": evidence.source_url,
                            "published_at": (
                                evidence.metadata.published_at.isoformat()
                                if evidence.metadata.published_at
                                else None
                            ),
                            "reference_at": (
                                evidence.metadata.reference_at.isoformat()
                                if evidence.metadata.reference_at
                                else None
                            ),
                            "materiality": evidence.metadata.materiality,
                            "materiality_reason": evidence.metadata.materiality_reason,
                            "pit_status": evidence.metadata.pit_status,
                            "ticker_refs": list(evidence.metadata.ticker_refs),
                        },
                        "reasoning_input_chars": len(prompt),
                        "reasoning_evidence_chars": len(
                            json.dumps(reasoning_evidence, ensure_ascii=False)
                        ),
                        "full_evidence_chars": len(
                            json.dumps(
                                evidence_to_dict(evidence),
                                ensure_ascii=False,
                                default=str,
                            )
                        ),
                        "ollama_defaults": {
                            "timeout_seconds": OllamaClient().timeout,
                            "num_ctx": OllamaClient().num_ctx,
                            "num_predict": OllamaClient().num_predict,
                            "keep_alive": OllamaClient().keep_alive,
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0

        stage = "ollama_preflight"
        deepseek_client = OllamaClient()
        preflight = ollama_preflight(client=deepseek_client)

        stage = "deepseek_reasoning"
        deepseek = deepseek_client.ask(prompt)
        deepseek_payload = {
            "model": deepseek.model,
            "analysis": deepseek.content,
            "thinking_chars": len(deepseek.thinking),
            "input_chars": len(prompt),
            "timeout_seconds": deepseek_client.timeout,
            "num_ctx": deepseek_client.num_ctx,
            "num_predict": deepseek_client.num_predict,
            "keep_alive": deepseek_client.keep_alive,
            "total_duration_ns": deepseek.total_duration_ns,
            "load_duration_ns": deepseek.load_duration_ns,
            "prompt_eval_count": deepseek.prompt_eval_count,
            "prompt_eval_cached_count": deepseek.prompt_eval_cached_count,
            "prompt_eval_duration_ns": deepseek.prompt_eval_duration_ns,
            "eval_count": deepseek.eval_count,
            "eval_duration_ns": deepseek.eval_duration_ns,
        }

        stage = "openclaw_escalation"
        senior = OpenClawStructuredClient(
            agent=settings.openclaw_agent,
            model=settings.openclaw_model,
            timeout=settings.openclaw_timeout_seconds,
            executable=settings.openclaw_bin,
        )
        response = senior.complete_json(
            instructions=(
                "Você é a camada sênior da V4.2 em um replay histórico. "
                "Use exclusivamente o Evidence CVM canônico e a síntese DeepSeek fornecidos. "
                "Não invente dados, não transforme o replay em recomendação atual e não "
                "cite nenhuma fonte fora de evidence_refs."
            ),
            input_text=json.dumps(
                {
                    "ticker": ticker,
                    "evidence": reasoning_evidence,
                    "deepseek_dossier": deepseek_payload,
                    "allowed_evidence_refs": [evidence_ref],
                },
                ensure_ascii=False,
            ),
            schema_name="b3_v42_historical_official_replay_v1",
            schema=SENIOR_SCHEMA,
        )
        if not isinstance(response, dict):
            raise ValueError("OpenClaw replay response is not a JSON object")
        if any(key not in response for key in SENIOR_SCHEMA["required"]):
            raise ValueError("OpenClaw replay response is incomplete")
        refs = response.get("evidence_refs")
        if not isinstance(refs, list) or not set(refs).issubset({evidence_ref}):
            raise ValueError("OpenClaw replay referenced evidence outside the canonical bundle")

        artifact = {
            "status": "PASS",
            "ticker": ticker,
            "year": args.year,
            "as_of": datetime.now(timezone.utc).isoformat(),
            "registry_sync": registry_sync,
            "issuer": {
                "issuer_id": issuer.issuer_id,
                "cvm_code": issuer.cvm_code,
                "cnpj": issuer.cnpj,
                "legal_name": issuer.legal_name,
            },
            "selected_evidence": evidence_to_dict(evidence),
            "acceptance": {
                "real_official_evidence": True,
                "materiality": evidence.metadata.materiality,
                "materiality_reason": evidence.metadata.materiality_reason,
                "pit_status": evidence.metadata.pit_status,
                "deepseek_exercised": True,
                "openclaw_exercised": True,
                "unknown_evidence_refs": False,
                "zero_paid_acquisition": True,
            },
            "ollama_preflight": preflight.as_dict(),
            "deepseek": deepseek_payload,
            "openclaw": {
                "model": settings.openclaw_model,
                "analysis": response,
            },
            "duration_seconds": (
                datetime.now(timezone.utc) - started_at
            ).total_seconds(),
        }
        save_artifact(args.output, artifact)
        print(json.dumps(artifact, ensure_ascii=False, indent=2, default=str))
        return 0
    except Exception as exc:
        failure = {
            "status": "FAIL",
            "ticker": ticker,
            "year": args.year,
            "stage": stage,
            "error": f"{type(exc).__name__}: {exc}",
        }
        print(json.dumps(failure, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
