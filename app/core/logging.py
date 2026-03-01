"""Structured logging configuration for OfferTracker API.

Provides a pre-configured logger that every module should import::

    from app.core.logging import logger

All output goes to stderr (standard for 12-factor apps) with a clean,
structured format including timestamps and module names.
"""

import logging
import sys


def _setup_logger() -> logging.Logger:
    """Create and configure the application-wide logger."""
    _logger = logging.getLogger("offertracker")

    # Avoid adding duplicate handlers on hot-reload
    if _logger.handlers:
        return _logger

    _logger.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s.%(module)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    _logger.addHandler(handler)

    # Prevent log propagation to uvicorn's root logger (avoids duplicates)
    _logger.propagate = False

    return _logger


logger = _setup_logger()
