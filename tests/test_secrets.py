import sys
from pathlib import Path

from iaula import secrets
from iaula.config import load_config, migrate_local_secrets


def _base(root: Path) -> None:
    (root / "config.toml").write_text(
        '[portal]\nbase_url = "https://example.test"\n', encoding="utf-8")


def test_roundtrip(tmp_path: Path) -> None:
    secrets.set_item(tmp_path, "chat.api_key", "sk-test-1234")
    assert secrets.get_item(tmp_path, "chat.api_key") == "sk-test-1234"
    assert secrets.item_hint(tmp_path, "chat.api_key") == "···1234"
    assert secrets.has_item(tmp_path, "chat.api_key")


def test_vault_hides_plaintext(tmp_path: Path) -> None:
    secrets.set_item(tmp_path, "chat.api_key", "sk-super-secret")
    raw = secrets.vault_path(tmp_path).read_bytes()
    assert b"sk-super-secret" not in raw
    if sys.platform == "win32":
        assert secrets.method(tmp_path) == "dpapi"
    else:
        assert secrets.method(tmp_path) == "plain"


def test_delete_item(tmp_path: Path) -> None:
    secrets.set_item(tmp_path, "chat.api_key", "sk-1234")
    secrets.delete_item(tmp_path, "chat.api_key")
    assert secrets.get_item(tmp_path, "chat.api_key") == ""
    assert not secrets.has_item(tmp_path, "chat.api_key")


def test_config_reads_vault(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    _base(tmp_path)
    secrets.set_item(tmp_path, "chat.api_key", "sk-vault")
    secrets.set_item(tmp_path, "portal.password", "pw-vault")
    (tmp_path / "config.local.toml").write_text(
        '[portal]\nusername = "u"\n', encoding="utf-8")
    cfg = load_config(tmp_path)
    assert cfg.chat.api_key == "sk-vault"
    assert cfg.portal.password == "pw-vault"


def test_env_key_wins(tmp_path: Path, monkeypatch) -> None:
    _base(tmp_path)
    secrets.set_item(tmp_path, "chat.api_key", "sk-vault")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env")
    assert load_config(tmp_path).chat.api_key == "sk-env"


def test_migrate_bundled_key(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    _base(tmp_path)
    app = tmp_path / "app"
    app.mkdir()
    legacy = app / "bundled_key.txt"
    legacy.write_text("sk-legacy\n", encoding="utf-8")
    monkeypatch.setattr(sys, "executable", str(app / "IAulaVirtual.exe"))

    assert migrate_local_secrets(tmp_path) is True
    assert not legacy.exists()
    assert load_config(tmp_path).chat.api_key == "sk-legacy"


def test_migrate_local_secrets(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    _base(tmp_path)
    local = tmp_path / "config.local.toml"
    local.write_text(
        '[portal]\nusername = "u"\npassword = "pw-old"\n\n[chat]\napi_key = "sk-old"\n',
        encoding="utf-8")

    assert migrate_local_secrets(tmp_path) is True
    text = local.read_text(encoding="utf-8")
    assert "password" not in text
    assert "api_key" not in text
    assert "username" in text

    cfg = load_config(tmp_path)
    assert cfg.portal.password == "pw-old"
    assert cfg.chat.api_key == "sk-old"
    assert migrate_local_secrets(tmp_path) is False
