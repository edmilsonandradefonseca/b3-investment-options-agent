from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.dashboard_fixtures import prepare


if __name__ == "__main__":
    prepare(Path(os.environ["B3_AGENT_DATA_DIR"]).resolve())
