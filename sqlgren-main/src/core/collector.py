"""Varredura recursiva de arquivos .sql e metadados de conteúdo."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, List, Tuple


def collect_sql_files(queries_dir: Path) -> List[Path]:
    """Lista arquivos .sql em ordem estável, ignorando diretórios ocultos."""
    root = Path(queries_dir)
    if not root.exists() or not root.is_dir():
        return []
    files: List[Path] = []
    try:
        for path in root.rglob("*.sql"):
            try:
                if not path.is_file():
                    continue
                if any(part.startswith(".") for part in path.relative_to(root).parts):
                    continue
                files.append(path)
            except OSError:
                continue
    except OSError:
        return []
    return sorted(files, key=lambda p: p.as_posix().lower())


def file_sha1(content: str) -> str:
    return hashlib.sha1(content.encode("utf-8", errors="replace")).hexdigest()


def read_sql_file(path: Path) -> Tuple[str, Dict[str, Any]]:
    """Lê um .sql com fallback de encoding. Nunca levanta por decode."""
    raw = b""
    try:
        raw = Path(path).read_bytes()
    except OSError as exc:
        return "", {
            "erro": "io",
            "detalhe": str(exc),
            "bytes": 0,
            "hash": "",
            "encoding": None,
        }

    text = ""
    encoding = "utf-8"
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            text = raw.decode(enc)
            encoding = enc
            break
        except UnicodeDecodeError:
            continue
    if not text and raw:
        text = raw.decode("utf-8", errors="replace")
        encoding = "utf-8-replace"

    stripped = text.strip()
    return stripped, {
        "bytes": len(raw),
        "hash": file_sha1(stripped)[:12] if stripped else "",
        "encoding": encoding,
        "linhas": stripped.count("\n") + 1 if stripped else 0,
    }
