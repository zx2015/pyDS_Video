from pathlib import Path

from ds_video.config.credentials import (
    DsmConnectionSettings,
    clear_settings,
    load_settings,
    save_settings,
)


def test_save_and_load_settings_round_trip(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    key_path = tmp_path / "secret.key"

    settings = DsmConnectionSettings(
        host="192.168.1.10",
        port="5000",
        username="alice",
        password="s3cr3t!",
        secure=False,
    )
    save_settings(settings, config_path=config_path, key_path=key_path)

    loaded = load_settings(config_path=config_path, key_path=key_path)

    assert loaded == settings


def test_password_is_encrypted_at_rest(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    key_path = tmp_path / "secret.key"

    settings = DsmConnectionSettings(host="nas", port="5000", username="bob", password="hunter2")
    save_settings(settings, config_path=config_path, key_path=key_path)

    raw = config_path.read_text(encoding="utf-8")
    assert "hunter2" not in raw


def test_load_settings_returns_none_when_missing(tmp_path: Path) -> None:
    assert load_settings(config_path=tmp_path / "missing.json", key_path=tmp_path / "missing.key") is None


def test_clear_settings_removes_config_file(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    key_path = tmp_path / "secret.key"
    settings = DsmConnectionSettings(host="nas", port="5000", username="bob", password="hunter2")
    save_settings(settings, config_path=config_path, key_path=key_path)
    assert config_path.exists()

    clear_settings(config_path=config_path)

    assert not config_path.exists()
    # Clearing a config that never existed should be a no-op, not an error.
    clear_settings(config_path=config_path)


def test_load_or_create_key_fixes_loose_permissions_on_existing_key(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    key_path = tmp_path / "secret.key"
    settings = DsmConnectionSettings(host="nas", port="5000", username="bob", password="hunter2")
    save_settings(settings, config_path=config_path, key_path=key_path)

    key_path.chmod(0o644)  # simulate the key file being restored/copied with loose perms
    load_settings(config_path=config_path, key_path=key_path)

    assert (key_path.stat().st_mode & 0o777) == 0o600
