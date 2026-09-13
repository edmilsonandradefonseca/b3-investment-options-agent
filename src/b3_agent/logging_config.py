import logging
from pathlib import Path

from b3_agent.config import settings


LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

_FILE_HANDLER_NAME = "b3_agent_file_handler"
_CONSOLE_HANDLER_NAME = "b3_agent_console_handler"


def configure_logging() -> None:
    """Configure application-wide logging."""
    settings.logs_dir.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    formatter = logging.Formatter(LOG_FORMAT)

    file_handler_exists = any(
        getattr(handler, "name", None) == _FILE_HANDLER_NAME
        for handler in root_logger.handlers
    )

    if not file_handler_exists:
        file_handler = logging.FileHandler(
            Path(settings.logs_dir) / "b3_agent.log",
            encoding="utf-8",
        )
        file_handler.name = _FILE_HANDLER_NAME
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    console_handler_exists = any(
        getattr(handler, "name", None) == _CONSOLE_HANDLER_NAME
        for handler in root_logger.handlers
    )

    if not console_handler_exists:
        console_handler = logging.StreamHandler()
        console_handler.name = _CONSOLE_HANDLER_NAME
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """Return a logger for an application component."""
    configure_logging()
    return logging.getLogger(name)
