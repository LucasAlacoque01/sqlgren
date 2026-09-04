"""HTML SPA de arquivo único (CSS + JS inline)."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any, Dict


def esc(value: Any) -> str:
    return html.escape(str(value)) if value is not None else ""


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def load_template(template_name: str) -> str:
    template_path = _project_root() / "templates" / template_name
    if not template_path.exists():
        raise FileNotFoundError(f"Template não encontrado: {template_path}")
    return template_path.read_text(encoding="utf-8")


def _load_asset(*parts: str) -> str:
    path = _project_root().joinpath(*parts)
    if not path.exists():
        raise FileNotFoundError(f"Asset não encontrado: {path}")
    return path.read_text(encoding="utf-8")


def render_page(catalog: Dict[str, Any], template_name: str = "front.html") -> str:
    template = load_template(template_name)
    css = _load_asset("assets", "css", "styles.css")
    js = _load_asset("assets", "js", "app.js")

    payload = json.dumps(catalog, ensure_ascii=False)
    payload = payload.replace("<", "\\u003c").replace(">", "\\u003e")

    meta = catalog.get("meta", {})
    title = meta.get("title") or "Acervo"
    locale = meta.get("locale") or "pt"
    lang = "en" if str(locale).lower().startswith("en") else "pt-BR"
    pitch = meta.get("pitch") or "Acervo — static SQL observatory."

    return (
        template
        .replace("{{TITLE}}", esc(title))
        .replace("{{LANG}}", lang)
        .replace("{{PITCH}}", esc(pitch))
        .replace("/*{{CSS}}*/", css)
        .replace("{{DATA}}", payload)
        .replace("/*{{JS}}*/", js)
    )
