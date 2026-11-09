from __future__ import annotations

import json
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

from iaula.portal.client import Portal

_FILEMANAGER_MARKER = "M.form_filemanager.init(Y, "


class SubmissionError(RuntimeError):
    pass


@dataclass(frozen=True)
class UploadResult:
    itemid: int
    files: list[str]
    submitted: bool
    message: str


def _json_after(html: str, marker: str) -> list[dict]:
    out: list[dict] = []
    start = 0
    while True:
        i = html.find(marker, start)
        if i < 0:
            return out
        i += len(marker)
        depth = 0
        in_str = False
        esc = False
        for j in range(i, len(html)):
            c = html[j]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
                continue
            if c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    try:
                        out.append(json.loads(html[i:j + 1]))
                    except json.JSONDecodeError:
                        pass
                    start = j + 1
                    break
        else:
            return out


def _filemanager_config(html: str, itemid: int) -> dict:
    for cfg in _json_after(html, _FILEMANAGER_MARKER):
        if int(cfg.get("itemid") or 0) == itemid:
            return cfg
    raise SubmissionError(
        "No pude leer la configuración del gestor de archivos de la tarea."
    )


def _submission_form(soup: BeautifulSoup):
    for form in soup.find_all("form"):
        if form.find("input", {"name": "action", "value": "savesubmission"}):
            return form
    return None


def _submit_form(soup: BeautifulSoup):
    for form in soup.find_all("form"):
        if form.find("input", {"name": "action", "value": "submit"}):
            return form
    return None


def _has_submission(soup: BeautifulSoup) -> bool:
    return soup.find("input", {"name": "action", "value": "removesubmissionconfirm"}) is not None


def _button(form, name: str, fallback: str) -> str:
    el = form.find(attrs={"name": name})
    if el is None:
        return fallback
    return el.get("value") or el.get_text(" ", strip=True) or fallback


def _fields(form) -> dict[str, str]:
    data: dict[str, str] = {}
    for el in form.select("input[name], button[name], textarea[name], select[name]"):
        name = el.get("name")
        if not name or el.get("type") in {"submit", "button", "reset"}:
            continue
        if el.get("type") == "checkbox" and not el.has_attr("checked"):
            continue
        if el.name == "textarea":
            data[name] = el.get_text()
        elif el.name == "select":
            opt = el.find("option", selected=True) or el.find("option")
            data[name] = (opt.get("value") or "") if opt is not None else ""
        else:
            data[name] = el.get("value") or ""
    return data


def _errors(soup: BeautifulSoup) -> list[str]:
    seen: list[str] = []
    for node in soup.select(".invalid-feedback, .alert-danger, .errorbox"):
        text = node.get_text(" ", strip=True)
        if text and text not in seen:
            seen.append(text)
    return seen


def _cmid(task_url: str) -> int:
    value = parse_qs(urlparse(task_url).query).get("id", [""])[0]
    if not value.isdigit():
        raise SubmissionError(f"No pude obtener el id del módulo de la tarea: {task_url}")
    return int(value)


def _check_files(paths: list[Path], cfg: dict) -> None:
    maxfiles = int(cfg.get("maxfiles") or 0)
    maxbytes = int(cfg.get("maxbytes") or 0)
    if maxfiles > 0 and len(paths) > maxfiles:
        raise SubmissionError(
            f"La tarea admite {maxfiles} archivo(s) y pediste {len(paths)}."
        )
    for path in paths:
        if not path.is_file():
            raise SubmissionError(f"No existe el archivo: {path}")
        if maxbytes > 0 and path.stat().st_size > maxbytes:
            mb = maxbytes / (1024 * 1024)
            raise SubmissionError(
                f"{path.name} supera el máximo permitido de {mb:g} MB."
            )


def _upload_file(portal: Portal, path: Path, cfg: dict, repo_id: str) -> dict:
    ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    params = {
        "action": "upload",
        "repo_id": repo_id,
        "p": "",
        "page": "",
        "env": "filemanager",
        "sesskey": portal.sesskey,
        "client_id": cfg.get("client_id", ""),
        "itemid": cfg["itemid"],
        "maxbytes": cfg.get("maxbytes", -1),
        "areamaxbytes": cfg.get("areamaxbytes", -1),
        "ctx_id": cfg["context"]["id"],
        "savepath": "/",
    }
    data = {
        "title": path.name,
        "author": (cfg.get("filepicker") or {}).get("author", ""),
        "license": (cfg.get("filepicker") or {}).get("defaultlicense") or "unknown",
    }
    with path.open("rb") as fh:
        resp = portal.http.post(
            f"{portal.base}/repository/repository_ajax.php?action=upload",
            params=params,
            data=data,
            files={"repo_upload_file": (path.name, fh, ctype)},
            timeout=300,
        )
    try:
        res = resp.json()
    except ValueError as exc:
        raise SubmissionError(
            f"Moodle rechazó la subida de {path.name} (HTTP {resp.status_code})."
        ) from exc
    if res.get("error"):
        raise SubmissionError(f"{path.name}: {res.get('error')}")
    if res.get("event") == "fileexists":
        raise SubmissionError(
            f"{path.name}: ya existe un archivo con ese nombre en la entrega."
        )
    if not res.get("url"):
        raise SubmissionError(f"Moodle no confirmó la subida de {path.name}.")
    return res


def upload_submission(
    portal: Portal,
    task_url: str,
    paths: list[Path],
    submit: bool = True,
) -> UploadResult:
    if not paths:
        raise SubmissionError("No indicaste ningún archivo.")
    cmid = _cmid(task_url)
    edit_url = f"{portal.base}/mod/assign/view.php?id={cmid}&action=editsubmission"
    html = portal.get(edit_url).text
    soup = BeautifulSoup(html, "html.parser")
    form = _submission_form(soup)
    if form is None:
        raise SubmissionError(
            "La tarea no admite entregas en este momento (cerrada, ya enviada "
            "o sin formulario de envío)."
        )
    fm_input = form.find("input", {"id": "id_files_filemanager"})
    if fm_input is None:
        fm_input = next(
            (i for i in form.select("input[name$='_filemanager']") if i.get("name")),
            None,
        )
    if fm_input is None:
        raise SubmissionError("La tarea no tiene un campo de archivos para adjuntar.")
    itemid = int(fm_input.get("value") or 0)
    fm_cfg = _filemanager_config(html, itemid)
    fp_cfg = fm_cfg.get("filepicker") or {}
    repos = fp_cfg.get("repositories") or {}
    upload_repo = next((r for r in repos.values() if r.get("type") == "upload"), None)
    if upload_repo is None:
        raise SubmissionError("El aula no ofrece el repositorio de subida de archivos.")
    _check_files(paths, fm_cfg)

    for path in paths:
        _upload_file(portal, path, fm_cfg, upload_repo["id"])

    data = _fields(form)
    data[fm_input["name"]] = str(itemid)
    data["submitbutton"] = _button(form, "submitbutton", "Guardar cambios")
    action = form.get("action") or edit_url
    resp = portal.http.post(action, data=data, timeout=120)
    result = BeautifulSoup(resp.text, "html.parser")
    errors = _errors(result)
    if errors:
        raise SubmissionError("; ".join(errors))

    message = "Archivos adjuntados a la tarea."
    submitted = _has_submission(result)
    if not submitted:
        resp = portal.http.get(f"{portal.base}/mod/assign/view.php?id={cmid}", timeout=60)
        result = BeautifulSoup(resp.text, "html.parser")
        submitted = _has_submission(result)
    if submit:
        form = _submit_form(result)
        if form is not None:
            payload = _fields(form)
            if form.find("input", {"name": "submissionstatement"}):
                payload["submissionstatement"] = "1"
            payload.setdefault("submitbutton", _button(form, "submitbutton", "Enviar tarea"))
            resp = portal.http.post(form.get("action") or action, data=payload, timeout=120)
            result = BeautifulSoup(resp.text, "html.parser")
            errors = _errors(result)
            if errors:
                raise SubmissionError("; ".join(errors))
            submitted = True
            message = "Tarea enviada."
        elif submitted:
            message = "Archivos adjuntados; la tarea quedó enviada para calificar."
        else:
            message = "Archivos adjuntados, pero no encontré el botón de envío de la tarea."

    return UploadResult(
        itemid=itemid,
        files=[path.name for path in paths],
        submitted=submitted,
        message=message,
    )
