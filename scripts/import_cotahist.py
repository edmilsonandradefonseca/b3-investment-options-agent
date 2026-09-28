"""Load selected historical cash-market tickers from a downloaded B3 ZIP."""

import argparse
import json
from pathlib import Path

from b3_agent.config import settings
from b3_agent.ingestion.cotahist import import_cotahist_zip


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", required=True, type=Path, help="Downloaded B3 COTAHIST annual ZIP")
    parser.add_argument("--tickers", required=True, help="Comma-separated cash-market tickers")
    parser.add_argument("--apply", action="store_true", help="Write archive (default: validate only)")
    args = parser.parse_args()
    destination = settings.data_dir / "archive" / "cotahist_raw"
    counts = import_cotahist_zip(
        args.zip, set(args.tickers.split(",")), destination, dry_run=not args.apply
    )
    print(json.dumps({"mode": "apply" if args.apply else "dry_run", "source": str(args.zip),
                      "destination": str(destination), "records_by_ticker": counts}, sort_keys=True))


if __name__ == "__main__":
    main()
