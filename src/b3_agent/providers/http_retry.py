from __future__ import annotations

import json
import os
import time
from collections.abc import Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_RETRY_HTTP_CODES = frozenset({408, 425, 429, 500, 502, 503, 504})


class ProviderRequestError(RuntimeError):
    """Network/provider failure after bounded retries."""


def request_json(
    request: Request,
    *,
    provider: str,
    timeout_env: str,
    default_timeout: float,
    retry_http_codes: Iterable[int] = DEFAULT_RETRY_HTTP_CODES,
    attempts_env: str = "B3_PROVIDER_HTTP_ATTEMPTS",
    default_attempts: int = 3,
) -> object:
    attempts = max(1, int(os.getenv(attempts_env, str(default_attempts))))
    timeout = max(1.0, float(os.getenv(timeout_env, str(default_timeout))))
    base_delay = max(
        0.0,
        float(os.getenv("B3_PROVIDER_RETRY_DELAY_SECONDS", "0.5")),
    )
    retry_codes = set(retry_http_codes)

    last_error: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            with urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            last_error = exc
            if exc.code not in retry_codes or attempt >= attempts:
                raise ProviderRequestError(
                    f"{provider} HTTP {exc.code} after {attempt} attempt(s)"
                ) from exc
        except (URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt >= attempts:
                raise ProviderRequestError(
                    f"{provider} request failed after {attempt} attempt(s): "
                    f"{type(exc).__name__}: {exc}"
                ) from exc

        if base_delay:
            time.sleep(base_delay * attempt)

    raise ProviderRequestError(
        f"{provider} request failed after {attempts} attempt(s): {last_error}"
    )
