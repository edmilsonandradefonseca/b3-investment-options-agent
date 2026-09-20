from __future__ import annotations

import re

from b3_agent.options.identity import canonical_option_ticker

# B3 option series: A-L are calls and M-X are puts.
_CALL_SERIES = frozenset("ABCDEFGHIJKL")
_PUT_SERIES = frozenset("MNOPQRSTUVWX")
_OPTION_TICKER_PATTERN = re.compile(r"^[A-Z0-9]+[A-X][0-9]{3}$")


def infer_b3_option_type(ticker: str) -> str | None:
    """Infer CALL/PUT from a valid B3 option ticker series letter.

    This is only a type fallback. It does not infer strike, expiration or
    underlying ticker, which require contract/reference data.
    """
    value = canonical_option_ticker(ticker)
    if not _OPTION_TICKER_PATTERN.fullmatch(value):
        return None
    series = value[-4].upper()
    if series in _CALL_SERIES:
        return "CALL"
    if series in _PUT_SERIES:
        return "PUT"
    return None
