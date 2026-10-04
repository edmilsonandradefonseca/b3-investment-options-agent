"""Bounded, process-local derived reuse. No new persistence or authority."""
from collections import OrderedDict
from concurrent.futures import Future
from copy import deepcopy
from hashlib import sha256
import json
from threading import Lock
from time import monotonic


def fingerprint(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str, allow_nan=False).encode()).hexdigest()


class ContextReuse:
    def __init__(self, *, capacity=64, ttl_seconds=30):
        self.capacity = capacity
        self.ttl_seconds = ttl_seconds
        self._values = OrderedDict()
        self._pending = {}
        self._lock = Lock()

    def get_or_build(self, key, build):
        started = monotonic()
        with self._lock:
            found = self._values.get(key)
            if found and monotonic() - found[0] < self.ttl_seconds:
                self._values.move_to_end(key)
                return deepcopy(found[1]), {"cache": "HIT", "latency_ms": (monotonic()-started)*1000}
            future = self._pending.get(key)
            owner = future is None
            if owner:
                future = Future()
                self._pending[key] = future
        if not owner:
            return deepcopy(future.result()), {"cache": "COALESCED", "latency_ms": (monotonic()-started)*1000}
        try:
            value = build()
            with self._lock:
                self._values[key] = (monotonic(), deepcopy(value))
                self._values.move_to_end(key)
                while len(self._values) > self.capacity:
                    self._values.popitem(last=False)
            future.set_result(deepcopy(value))
            return value, {"cache": "MISS", "latency_ms": (monotonic()-started)*1000}
        except BaseException as exc:
            future.set_exception(exc)
            raise
        finally:
            with self._lock:
                self._pending.pop(key, None)
