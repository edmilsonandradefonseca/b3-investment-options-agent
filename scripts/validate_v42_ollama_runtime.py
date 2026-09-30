#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from b3_agent.llm.ollama_client import OllamaClient
from b3_agent.llm.ollama_runtime import ollama_preflight


def main() -> int:
    client = OllamaClient()
    try:
        result = ollama_preflight(client=client)
        payload = {
            "status": "PASS",
            **result.as_dict(),
            "reasoning_contract": {
                "timeout_seconds": client.timeout,
                "num_ctx": client.num_ctx,
                "num_predict": client.num_predict,
                "keep_alive_after_real_inference": client.keep_alive,
            },
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "model": client.model,
                    "base_url": client.base_url,
                    "error": f"{type(exc).__name__}: {exc}",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
