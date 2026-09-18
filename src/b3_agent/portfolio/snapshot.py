from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from b3_agent.options.transactions import OptionsTransactionLoader
from b3_agent.portfolio.ingestion import BtgRendaVariavelLoader


PORTFOLIO_SNAPSHOT = "portfolio.xlsx"
OPTIONS_TRANSACTIONS_SNAPSHOT = "options_transactions.xlsx"


def load_active_snapshots(data_dir: str | Path) -> dict[str, Any]:
    """Load the currently active validated Excel snapshots.

    Each file is a point-in-time replacement snapshot. Missing snapshots are
    simply omitted so callers can still provide other deterministic inputs.
    """
    import_dir = Path(data_dir) / "imports"
    defaults: dict[str, Any] = {}

    portfolio_path = import_dir / PORTFOLIO_SNAPSHOT
    if portfolio_path.is_file():
        defaults["portfolio_context"] = BtgRendaVariavelLoader().load(portfolio_path)

    options_path = import_dir / OPTIONS_TRANSACTIONS_SNAPSHOT
    if options_path.is_file():
        transactions = OptionsTransactionLoader().load(options_path)
        defaults["options_transactions"] = tuple(asdict(item) for item in transactions)

    return defaults
