"""Logging setup (docs/design.md section 6): console + rotating file, per-module loggers."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from ds_video.config.paths import get_log_dir

_CONFIGURED = False


def configure_logging(level: int = logging.INFO) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    root = logging.getLogger("ds_video")
    root.setLevel(level)

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    file_handler = RotatingFileHandler(
        get_log_dir() / "ds_video.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    # These third-party HTTP libraries are chatty at INFO (one line per
    # request), which drowns out ds_video's own logs; only their warnings
    # and above are useful here.
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

    _CONFIGURED = True
