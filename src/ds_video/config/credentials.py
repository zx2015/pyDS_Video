"""Encrypted local storage for DSM connection settings and credentials.

Per docs/design.md section 5: the password is encrypted with a symmetric key
(``cryptography``'s Fernet) stored in a separate key file in the same config
directory. This does not depend on an OS keychain, matching the confirmed
requirement.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from ds_video.config.paths import get_config_path, get_key_path


@dataclass
class DsmConnectionSettings:
    """Everything needed to connect to one DSM server."""

    host: str
    port: str
    username: str
    password: str
    secure: bool = False


def _load_or_create_key(key_path: Path) -> bytes:
    if key_path.exists():
        return key_path.read_bytes()
    key = Fernet.generate_key()
    key_path.write_bytes(key)
    try:
        key_path.chmod(0o600)
    except OSError:
        # Best effort: not all filesystems support POSIX permissions.
        pass
    return key


def save_settings(settings: DsmConnectionSettings, config_path: Optional[Path] = None, key_path: Optional[Path] = None) -> None:
    """Persist connection settings, with the password encrypted at rest."""
    config_path = config_path or get_config_path()
    key_path = key_path or get_key_path()

    fernet = Fernet(_load_or_create_key(key_path))
    encrypted_password = fernet.encrypt(settings.password.encode("utf-8")).decode("ascii")

    payload = asdict(settings)
    payload["password"] = encrypted_password

    config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    try:
        config_path.chmod(0o600)
    except OSError:
        pass


def load_settings(config_path: Optional[Path] = None, key_path: Optional[Path] = None) -> Optional[DsmConnectionSettings]:
    """Load previously saved connection settings, decrypting the password.

    Returns ``None`` if no settings have been saved yet.
    """
    config_path = config_path or get_config_path()
    key_path = key_path or get_key_path()

    if not config_path.exists() or not key_path.exists():
        return None

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    fernet = Fernet(key_path.read_bytes())
    try:
        password = fernet.decrypt(payload["password"].encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Stored credentials could not be decrypted (corrupt or wrong key).") from exc

    return DsmConnectionSettings(
        host=payload["host"],
        port=payload["port"],
        username=payload["username"],
        password=password,
        secure=payload.get("secure", False),
    )


def clear_settings(config_path: Optional[Path] = None) -> None:
    """Remove any saved connection settings (e.g. on user logout)."""
    config_path = config_path or get_config_path()
    if config_path.exists():
        config_path.unlink()
