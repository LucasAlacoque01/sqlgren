"""Catálogo máquina-legível."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def exportar_catalogo_json(catalog: Dict[str, Any], output_dir: Path, filename: str = "catalogo.json") -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / filename
    out_file.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_file
