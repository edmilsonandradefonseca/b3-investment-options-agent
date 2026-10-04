"""Exact-input reuse for derived model output; process-local and bounded."""
import json
from threading import local
from time import monotonic
from b3_agent.intelligence.reuse import ContextReuse, fingerprint


class ReusingLLMClient:
    def __init__(self, client, *, ttl_seconds=60):
        self.client = client
        self._cache = ContextReuse(capacity=32, ttl_seconds=ttl_seconds)
        self._thread = local()

    @property
    def last_telemetry(self):
        return getattr(self._thread, "telemetry", {})

    def complete_json(self, *, instructions, input_text, schema_name, schema):
        # Whitespace compaction only; never remove timestamps, contradictions or unknowns.
        try:
            compact = json.dumps(json.loads(input_text), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        except (ValueError, TypeError):
            compact = input_text
        key = fingerprint([instructions, compact, schema_name, schema])
        started = monotonic()
        def invoke():
            result = self.client.complete_json(instructions=instructions, input_text=compact, schema_name=schema_name, schema=schema)
            if not isinstance(result, dict) or any(k not in result for k in schema.get("required", [])):
                raise ValueError("Invalid structured model result; not cached")
            return result
        try:
            result, telemetry = self._cache.get_or_build(key, invoke)
            self._thread.telemetry = {**telemetry, "schema": schema_name, "fingerprint": key, "input_chars": len(compact), "output_chars": len(json.dumps(result, default=str)), "total_ms": (monotonic()-started)*1000}
            return result
        except Exception:
            self._thread.telemetry = {"cache": "ERROR", "schema": schema_name, "total_ms": (monotonic()-started)*1000}
            raise
