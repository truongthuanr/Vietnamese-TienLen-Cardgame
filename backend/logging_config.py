import logging
import os
import sys


def configure_logging() -> None:
    """Configure app logging to stdout for container-friendly collection."""
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    app_logger = logging.getLogger("tienlen")
    app_logger.setLevel(level)
    app_logger.handlers.clear()
    app_logger.addHandler(handler)
    app_logger.propagate = False

