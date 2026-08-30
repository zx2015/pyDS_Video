"""Platform-specific storage locations for ds_video's config, credentials and logs.

Per docs/design.md section 4/5:
- macOS: ``~/Library/Application Support/ds_video/``
- Linux: XDG config dir, i.e. ``$XDG_CONFIG_HOME/ds_video`` or ``~/.config/ds_video``
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def get_app_dir() -> Path:
    """Return (and create) the per-user directory ds_video stores its data in."""
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", "")) if os.environ.get("XDG_CONFIG_HOME") else Path.home() / ".config"
    app_dir = base / "ds_video"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def get_config_path() -> Path:
    return get_app_dir() / "config.json"


def get_key_path() -> Path:
    return get_app_dir() / "secret.key"


def get_log_dir() -> Path:
    log_dir = get_app_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir
