from pathlib import Path

from iaula import google_session, gui, proc
from iaula.config import load_config, save_local
from iaula.gui import speech_text


def _base(tmp_path: Path) -> None:
    (tmp_path / "config.toml").write_text(
        '[portal]\nbase_url = "https://example.test"\n', encoding="utf-8")


def test_browser_preference_from_local(tmp_path: Path) -> None:
    _base(tmp_path)
    (tmp_path / "config.local.toml").write_text(
        '[browser]\ndefault = "brave"\n', encoding="utf-8")
    assert load_config(tmp_path).browser == "brave"


def test_browser_legacy_notebooklm_key(tmp_path: Path) -> None:
    _base(tmp_path)
    (tmp_path / "config.local.toml").write_text(
        '[notebooklm]\nbrowser = "chrome"\n', encoding="utf-8")
    assert load_config(tmp_path).browser == "chrome"


def test_save_browser_preserves_sections(tmp_path: Path) -> None:
    _base(tmp_path)
    (tmp_path / "config.local.toml").write_text(
        '[portal]\nusername = "u"\npassword = "p"\n', encoding="utf-8")
    save_local(tmp_path, "browser", {"default": "msedge"})
    cfg = load_config(tmp_path)
    assert cfg.browser == "msedge"
    assert cfg.portal.username == "u"
    assert cfg.portal.password == "p"


def test_speech_text_strips_markdown() -> None:
    assert speech_text("**Hola**\n\n`mundo` *cruel*") == "Hola mundo cruel"


def test_run_hides_console(monkeypatch) -> None:
    seen: dict = {}

    def fake(args, **kwargs):
        seen.update(kwargs)
        return None

    monkeypatch.setattr(proc.subprocess, "run", fake)
    proc.run(["cmd", "/c", "echo", "hola"])
    if proc.sys.platform == "win32":
        assert seen["creationflags"] & 0x08000000
        assert seen["startupinfo"].dwFlags & proc.subprocess.STARTF_USESHOWWINDOW


def test_google_session_paths(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    profile = tmp_path / "BraveSoftware" / "Brave-Browser" / "User Data"
    profile.mkdir(parents=True)
    assert google_session.user_data_dir("brave") == profile
    assert google_session.user_data_dir("chrome") is None
    assert google_session.process_name("brave") == "brave.exe"


def test_single_instance_binding() -> None:
    if proc.sys.platform == "win32":
        assert gui.LocalServer.allow_reuse_address is False


