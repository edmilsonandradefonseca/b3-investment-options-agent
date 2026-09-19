from __future__ import annotations

from b3_agent.options.identity import canonical_option_ticker

# B3 option series: A-L are calls and M-X are puts.
_CALL_SERIES = frozenset("ABCDEFGHIJKL")
_PUT_SERIES = frozenset("MNOPQRSTUVWX")


def infer_b3_option_type(ticker: str) -> str | None:
    """Infer CALL/PUT from the B3 option series letter.

    This is only a type fallback. It does not infer strike, expiration or
    underlying ticker, which require contract/reference data.
    """
    value = canonical_option_ticker(ticker)
    token = value.split()[0] if value.split() else value
    letters = [char.upper() for char in token if char.isalpha()]
    if not letters:
        return None
    series = letters[-1]
    if series in _CALL_SERIES:
        return "CALL"
    if series in _PUT_SERIES:
        return "PUT"
    return None
