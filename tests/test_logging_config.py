from pathlib import Path

from b3_agent.config import settings
from b3_agent.logging_config import get_logger


def test_logger_is_created():
    logger = get_logger("b3_agent.test")

    assert logger.name == "b3_agent.test"


def test_log_file_is_created():
    logger = get_logger("b3_agent.test_file")

    logger.info("logging test")

    log_file = Path(settings.logs_dir) / "b3_agent.log"

    assert log_file.exists()
