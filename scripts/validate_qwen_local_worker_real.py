"""Isolated Qwen admission test on reviewed public reports; no production writes."""
import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic
from urllib.request import Request, urlopen

from b3_agent.institution_target_ingestion import reviewed_evidence
from b3_agent.intelligence.local_evidence_analysis import LocalEvidenceAnalyst, LocalEvidenceQueue
from b3_agent.jobs.primary_targets import enqueue_target
from b3_agent.llm.ollama_client import OllamaClient
from validate_live_workspace_outputs import write_private_report


def main():
    model = "qwen3:4b-instruct-2507-q4_K_M"
    client = OllamaClient(model=model, num_ctx=4096, num_predict=2048,
                          timeout=600, think=False, keep_alive=0)
    with urlopen(Request(client.base_url + "/api/pull",
                         data=json.dumps({"model": model, "stream": False}).encode(),
                         headers={"Content-Type": "application/json"}), timeout=600) as response:
        result = json.loads(response.read())
    assert result.get("status") == "success", "Model acquisition did not complete"
    manifest = json.loads((Path(__file__).resolve().parents[1] /
                           "docs/research/institution_targets_reviewed.json").read_text())
    results = []
    with TemporaryDirectory(prefix="b3-qwen-admission-") as directory:
        queue = LocalEvidenceQueue(Path(directory))
        for raw in manifest["evidence"]:
            if raw["metadata"]["extra"]["price_target"]["institution"] != "XP":
                continue
            enqueue_target(queue, reviewed_evidence(raw, datetime.now(timezone.utc)))
        for request in queue.pending():
            started = monotonic()
            dossier = LocalEvidenceAnalyst(client).analyze(request)
            elapsed = round((monotonic() - started) * 1000, 1)
            write_private_report(Path.home() / ".local/share/b3-investment-options-agent/live-validation/qwen-admission",
                                 dossier.as_dict())
            row = {"case": "QWEN_TARGET_ADMISSION", "ticker": request.ticker,
                   "model": dossier.model, "status": dossier.status.value,
                   "quality_flags": list(dossier.quality_flags), "elapsed_ms": elapsed,
                   "eval_count": dossier.eval_count, "thinking_chars": dossier.thinking_chars,
                   "num_predict": dossier.num_predict}
            results.append(row)
            print(json.dumps(row), flush=True)
    assert len(results) == 2 and all(row["status"] == "READY" for row in results), "Qwen target admission incomplete"
    print("QWEN_REAL_ADMISSION=PASS isolated-public-targets; content review and deployment pending", flush=True)


if __name__ == "__main__":
    main()
