"""Máscara de PII para catálogos compartilháveis. Não apaga o sinal — só o valor."""

from __future__ import annotations

import copy
import re
from typing import Any, Dict

from .pii import _LITERAL_CNS, _LITERAL_CPF, _LITERAL_EMAIL

_LONG_DIGIT = re.compile(r"\b\d{8,}\b")
_QUOTED_SECRET = re.compile(
    r"(?i)((?:senha|password|passwd|pwd|token|secret|api_key|apikey)\s*=\s*)('([^']*)'|\"([^\"]*)\")"
)


def redact_sql(sql: str) -> str:
    text = sql or ""
    text = _LITERAL_EMAIL.sub("[REDACTED_EMAIL]", text)
    text = _LITERAL_CPF.sub("[REDACTED_ID]", text)
    text = _QUOTED_SECRET.sub(r"\1'[REDACTED]'", text)
    text = _LITERAL_CNS.sub("[REDACTED_HEALTH_ID]", text)
    text = _LONG_DIGIT.sub("[REDACTED_NUM]", text)
    return text


def _redact_block(block: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(block)
    for key in ("sql", "sql_pretty", "comentario"):
        if out.get(key):
            out[key] = redact_sql(str(out[key]))
    targets = out.get("sql_targets") or {}
    if isinstance(targets, dict):
        out["sql_targets"] = {k: redact_sql(str(v)) if v else v for k, v in targets.items()}
    filtros = out.get("filtros") or []
    if filtros:
        out["filtros"] = [redact_sql(str(f)) for f in filtros]
    return out


def redact_catalog(catalog: Dict[str, Any]) -> Dict[str, Any]:
    """Devolve uma cópia pronta para compartilhar: SQL mascarado, metadados de PII intactos."""
    out = copy.deepcopy(catalog)
    out["queries"] = [_redact_block(q) for q in (out.get("queries") or [])]
    meta = dict(out.get("meta") or {})
    meta["redacted"] = True
    meta["shareable"] = True
    out["meta"] = meta
    return out
