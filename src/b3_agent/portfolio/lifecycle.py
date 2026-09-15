from __future__ import annotations

from dataclasses import dataclass
from datetime import date


LIFECYCLE_STATES = (
    "OPEN", "MONITOR", "RE_EVALUATE", "HOLD", "CLOSE", "ROLL",
    "REPLACE", "ASSIGN", "EXERCISE", "NEW",
)


@dataclass(frozen=True)
class PositionLifecycle:
    position_id: str
    state: str
    as_of: date
    reason: str = ""

    def __post_init__(self) -> None:
        if self.state not in LIFECYCLE_STATES:
            raise ValueError(f"invalid lifecycle state: {self.state}")


class PositionLifecycleEngine:
    """Deterministic lifecycle state machine; no autonomous trading actions."""

    def open(self, position_id: str, as_of: date) -> PositionLifecycle:
        return PositionLifecycle(position_id, "OPEN", as_of)

    def transition(self, current: PositionLifecycle, target: str, *, reason: str = "") -> PositionLifecycle:
        allowed = {
            "OPEN": {"MONITOR", "RE_EVALUATE", "CLOSE", "HOLD"},
            "MONITOR": {"RE_EVALUATE", "HOLD", "CLOSE", "ROLL", "REPLACE", "ASSIGN", "EXERCISE"},
            "RE_EVALUATE": {"HOLD", "CLOSE", "ROLL", "REPLACE", "ASSIGN", "EXERCISE", "MONITOR"},
            "HOLD": {"MONITOR", "RE_EVALUATE", "CLOSE", "ROLL", "REPLACE"},
            "CLOSE": {"NEW"},
            "ROLL": {"NEW"},
            "REPLACE": {"NEW"},
            "ASSIGN": {"NEW"},
            "EXERCISE": {"NEW"},
            "NEW": {"OPEN"},
        }
        if target not in allowed[current.state]:
            raise ValueError(f"invalid lifecycle transition: {current.state} -> {target}")
        return PositionLifecycle(current.position_id, target, current.as_of, reason)
