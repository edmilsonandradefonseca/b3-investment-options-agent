#!/usr/bin/env python3
from __future__ import annotations

import os

from b3_agent.jobs.macro_refresh import MacroRefreshJob, local_today


def main() -> None:
    lookback_days = int(os.getenv("B3_MACRO_LOOKBACK_DAYS", "120"))
    result = MacroRefreshJob(lookback_days=lookback_days).run(
        as_of=local_today()
    )
    values = " ".join(
        f"{name}={value}"
        for name, value in sorted(result.latest_values.items())
    )
    print(
        "MACRO REFRESH OK "
        f"window={result.start.isoformat()}..{result.end.isoformat()} "
        f"fetched={result.fetched} inserted={result.inserted} "
        f"duplicates={result.duplicates} {values}"
    )


if __name__ == "__main__":
    main()
