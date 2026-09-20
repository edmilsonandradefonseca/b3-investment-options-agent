from __future__ import annotations

import os
from pathlib import Path

from tests.dashboard_fixtures import prepare


if __name__ == "__main__":
    prepare(Path(os.environ["B3_AGENT_DATA_DIR"]).resolve())
