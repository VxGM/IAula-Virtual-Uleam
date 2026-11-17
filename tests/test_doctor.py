from pathlib import Path

from iaula import doctor
from iaula.config import load_config


def _cfg(tmp_path: Path, monkeypatch) -> object:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    (tmp_path / "config.toml").write_text(
        '[portal]\nbase_url = "https://example.test"\n', encoding="utf-8")
    (tmp_path / "config.local.toml").write_text(
        '[portal]\nusername = "u"\npassword = "p"\n', encoding="utf-8")
    return load_config(tmp_path)


def test_check_all_shape(tmp_path: Path, monkeypatch) -> None:
    result = doctor.check_all(_cfg(tmp_path, monkeypatch), network=False)
    assert set(result) == {"checked_at", "summary", "items", "fatal"}
    assert result["fatal"] is False

    ids = {item["id"] for item in result["items"]}
    assert {"runtime", "deps", "browser", "chromium", "portal_config",
            "session", "network", "disk", "secrets", "legacy_key",
            "ai", "notebooklm"}.issubset(ids)

    summary = result["summary"]
    total = summary["ok"] + summary["warn"] + summary["error"] + summary["skip"]
    assert total == len(result["items"])

    network = next(item for item in result["items"] if item["id"] == "network")
    assert network["status"] == "skip"

    for item in result["items"]:
        assert item["status"] in {"ok", "warn", "error", "skip"}
        assert isinstance(item["fatal"], bool)
        assert isinstance(item["fixable"], bool)


def test_repair_removes_session(tmp_path: Path, monkeypatch) -> None:
    cfg = _cfg(tmp_path, monkeypatch)
    session = tmp_path / "data" / "session.json"
    session.parent.mkdir(parents=True)
    session.write_text("{}", encoding="utf-8")

    result = doctor.repair(cfg, ["session"], log=lambda _line: None)
    assert result["repaired"] == ["session"]
    assert not session.exists()


def test_repair_rejects_unknown(tmp_path: Path, monkeypatch) -> None:
    cfg = _cfg(tmp_path, monkeypatch)
    result = doctor.repair(cfg, ["no-existe"], log=lambda _line: None)
    assert result["repaired"] == []
    assert result["failed"][0]["id"] == "no-existe"
