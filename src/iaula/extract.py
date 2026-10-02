from __future__ import annotations

from pathlib import Path

TEXT_EXT = {".txt", ".md", ".csv", ".json", ".html", ".htm", ".py", ".js", ".css", ".tsv"}


def extract_text(path: Path, max_chars: int = 12000) -> str:
    ext = path.suffix.lower()
    if ext in TEXT_EXT:
        data = path.read_text(encoding="utf-8", errors="replace")
    elif ext == ".pdf":
        data = _pdf_text(path)
    else:
        raise ValueError(f"Tipo no soportado: {ext} (soportados: PDF, txt, md, csv, html, json)")
    if len(data) > max_chars:
        data = data[:max_chars] + f"\n… (truncado; {len(data)} caracteres en total)"
    return data


def _pdf_text(path: Path) -> str:
    try:
        import pymupdf
    except ImportError as exc:
        raise RuntimeError("Falta pymupdf: pip install pymupdf") from exc
    doc = pymupdf.open(path)
    try:
        return "\n".join(page.get_text() for page in doc)
    finally:
        doc.close()
