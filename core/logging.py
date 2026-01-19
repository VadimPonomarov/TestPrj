import logging
import os
import sys
from typing import Final

_LOG_FORMAT: Final[str] = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"


def configure_logger(name: str) -> logging.Logger:
    """Return a module-level logger configured for structured output."""

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    root_logger = logging.getLogger()
    if root_logger.handlers:
        return logger

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))

    logger.setLevel(log_level)
    logger.addHandler(handler)
    logger.propagate = False

    return logger
