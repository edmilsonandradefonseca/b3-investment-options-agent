from __future__ import annotations

from dataclasses import dataclass
import json
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from b3_agent.llm.ollama_client import OllamaClient


@dataclass(frozen=True, slots=True)
class OllamaPreflightResult:
    model: str
    ollama_version: str | None
    installed_models: tuple[str, ...]
    loaded_models_before: tuple[str, ...]
    loaded_models_after: tuple[str, ...]
    elapsed_seconds: float
    done: bool
    done_reason: str | None
    load_duration_ns: int | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "ollama_version": self.ollama_version,
            "installed_models": list(self.installed_models),
            "loaded_models_before": list(self.loaded_models_before),
            "loaded_models_after": list(self.loaded_models_after),
            "elapsed_seconds": self.elapsed_seconds,
            "done": self.done,
            "done_reason": self.done_reason,
            "load_duration_ns": self.load_duration_ns,
        }


def ollama_preflight(
    *,
    client: OllamaClient | None = None,
    warm_timeout: float = 180.0,
) -> OllamaPreflightResult:
    """Validate Ollama/model availability and preload the model without inference.

    Ollama documents an empty chat request as the supported way to load a model
    into memory. A successful load is expected to return empty assistant
    content, so preflight must validate transport/status and /api/ps state
    rather than require generated text.
    """
    base = client or OllamaClient()
    version_payload = _get_json(f"{base.base_url}/api/version", timeout=15.0)
    version = str(version_payload.get("version") or "").strip() or None

    installed = _model_names(
        _get_json(f"{base.base_url}/api/tags", timeout=15.0)
    )
    if not _model_available(base.model, installed):
        raise RuntimeError(
            f"Ollama model is not installed: {base.model}; "
            f"installed={','.join(installed) or 'none'}"
        )

    before = _model_names(
        _get_json(f"{base.base_url}/api/ps", timeout=15.0)
    )

    started = time.monotonic()
    loaded = _post_json(
        f"{base.base_url}/api/chat",
        {
            "model": base.model,
            "messages": [],
            "stream": False,
            "keep_alive": "5m",
        },
        timeout=min(float(warm_timeout), base.timeout),
    )
    elapsed = time.monotonic() - started

    if not bool(loaded.get("done", False)):
        raise RuntimeError(
            f"Ollama preload did not complete for model {base.model}: {loaded!r}"
        )

    after = _model_names(
        _get_json(f"{base.base_url}/api/ps", timeout=15.0)
    )
    if not _model_available(base.model, after):
        raise RuntimeError(
            f"Ollama preload completed but model is not resident: "
            f"{base.model}; loaded={','.join(after) or 'none'}"
        )

    return OllamaPreflightResult(
        model=str(loaded.get("model") or base.model),
        ollama_version=version,
        installed_models=installed,
        loaded_models_before=before,
        loaded_models_after=after,
        elapsed_seconds=round(elapsed, 3),
        done=True,
        done_reason=(
            str(loaded.get("done_reason")).strip()
            if loaded.get("done_reason") is not None
            else None
        ),
        load_duration_ns=_as_int(loaded.get("load_duration")),
    )


def _get_json(url: str, *, timeout: float) -> dict[str, Any]:
    request = Request(url, headers={"Accept": "application/json"}, method="GET")
    return _request_json(request, timeout=timeout, label=f"GET {url}")


def _post_json(
    url: str,
    payload: dict[str, Any],
    *,
    timeout: float,
) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    return _request_json(request, timeout=timeout, label=f"POST {url}")


def _request_json(
    request: Request,
    *,
    timeout: float,
    label: str,
) -> dict[str, Any]:
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        raise RuntimeError(
            f"Ollama runtime probe failed {label}: "
            f"{type(exc).__name__}: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeError(
            f"Ollama runtime probe returned invalid payload: {label}"
        )
    error = payload.get("error")
    if error:
        raise RuntimeError(
            f"Ollama runtime probe returned error {label}: {error}"
        )
    return payload


def _model_names(payload: dict[str, Any]) -> tuple[str, ...]:
    raw = payload.get("models") or ()
    names: list[str] = []
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            value = str(item.get("name") or item.get("model") or "").strip()
            if value and value not in names:
                names.append(value)
    return tuple(names)


def _model_available(model: str, available: tuple[str, ...]) -> bool:
    if model in available:
        return True
    if ":" not in model and f"{model}:latest" in available:
        return True
    return False


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
