"""B3 V4 Streamlit dashboard entrypoint.

The UI is a read-only presentation surface over deterministic/statistical V4
services. Business logic remains in domain services; no order execution is
available from this entrypoint.
"""

from app_v06 import *  # noqa: F401,F403
