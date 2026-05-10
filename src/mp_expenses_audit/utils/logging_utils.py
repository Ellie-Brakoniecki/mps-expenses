"""Logging helpers for audit-traceable processing."""

import logging


def configure_logging(level: int = logging.INFO) -> None:
    """Configure consistent package-level logging."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )