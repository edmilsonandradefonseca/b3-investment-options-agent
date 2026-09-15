from __future__ import annotations

"""Canonical identity rules for B3 option tickers.

Source-specific representations are preserved. Canonicalization is used only
for cross-source identity matching.
"""

_KNOWN_MARKET_SUFFIXES = frozenset({"ON", "PN", "DR1"})


def canonical_option_ticker(ticker: str) -> str:
    """Return the canonical option identity without destroying source notation."""
    value = " ".join(str(ticker).strip().split())

    if not value:
        raise ValueError("option ticker cannot be empty")

    parts = value.split()

    if len(parts) > 1 and parts[-1].upper() in _KNOWN_MARKET_SUFFIXES:
        return " ".join(parts[:-1])

    return value
