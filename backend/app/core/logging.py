"""Central logging configuration. No stray print() statements anywhere else."""
from __future__ import annotations

import logging
import sys

from .config import settings


def configure_logging() -> None:
    root = logging.getLogger()
    if root.handlers:
        return  # already configured (e.g. re-import under uvicorn --reload)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    root.addHandler(handler)
    root.setLevel(settings.log_level.upper())

    # Keep noisy libraries at a reasonable level
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
