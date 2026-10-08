from __future__ import annotations

from dataclasses import dataclass


# Explicit BTG reference aliases observed in authoritative Renda Variavel
# snapshots. Source identifiers are never mutated; aliases are used only for
# deterministic economic aggregation.
BTG_UNDERLYING_ALIASES: dict[str, str] = {
    "PETRPN": "PETR4",
    "GGBRPN": "GGBR4",
    "BRADPN": "BBDC4",
    "CMIGPN": "CMIG4",
    "VALEON": "VALE3",
}


@dataclass(frozen=True)
class InstrumentIdentityResolver:
    aliases: dict[str, str] | None = None

    def resolve(self, ticker: str) -> str:
        normalized = ticker.strip().upper()
        mapping = self.aliases if self.aliases is not None else BTG_UNDERLYING_ALIASES
        return mapping.get(normalized, normalized)
