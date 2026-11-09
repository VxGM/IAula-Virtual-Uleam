from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from iaula.portal.submission import (
    SubmissionError,
    _check_files,
    _cmid,
    _errors,
    _fields,
    _json_after,
)

HTML = """
<script>
M.form_filemanager.init(Y, {"itemid":123,"maxfiles":1,"maxbytes":1024,
"filepicker":{"repositories":{"5":{"id":"5","type":"upload"}}}});
M.form_filemanager.init(Y, {"itemid":999,"maxfiles":2});
</script>
<form action="https://x/mod/assign/view.php" method="post">
  <input name="sesskey" type="hidden" value="abc">
  <input name="_qf__mod_assign_submission_form" type="hidden" value="1">
  <input name="files_filemanager" type="hidden" id="id_files_filemanager" value="123">
  <textarea name="onlinetext_editor[text]">texto previo</textarea>
  <input name="submissionstatement" type="checkbox" value="1">
  <input name="submitbutton" type="submit" value="Guardar cambios">
</form>
<div class="invalid-feedback">Falta algo</div>
<div class="errorbox">Falta algo</div>
"""


def test_json_after_matches_balanced_objects() -> None:
    configs = _json_after(HTML, "M.form_filemanager.init(Y, ")
    assert [c["itemid"] for c in configs] == [123, 999]
    assert configs[0]["filepicker"]["repositories"]["5"]["type"] == "upload"


def test_fields_preserves_textarea_and_skips_unchecked() -> None:
    form = BeautifulSoup(HTML, "html.parser").find("form")
    data = _fields(form)
    assert data["sesskey"] == "abc"
    assert data["onlinetext_editor[text]"] == "texto previo"
    assert "submissionstatement" not in data
    assert "submitbutton" not in data


def test_errors_dedupes() -> None:
    soup = BeautifulSoup(HTML, "html.parser")
    assert _errors(soup) == ["Falta algo"]


def test_cmid() -> None:
    assert _cmid("https://x/mod/assign/view.php?id=584517&action=view") == 584517
    with pytest.raises(SubmissionError):
        _cmid("https://x/mod/assign/view.php")


def test_check_files_respects_limits(tmp_path: Path) -> None:
    small = tmp_path / "a.txt"
    small.write_text("hola", encoding="utf-8")
    _check_files([small], {"maxfiles": 1, "maxbytes": 1024})
    with pytest.raises(SubmissionError):
        _check_files([small, small], {"maxfiles": 1, "maxbytes": 1024})
    with pytest.raises(SubmissionError):
        _check_files([small], {"maxbytes": 1})
