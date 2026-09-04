"""Transpilação e formatação de SQL via sqlglot (nunca executa)."""

from __future__ import annotations

from typing import Dict, Optional, Sequence


DEFAULT_TARGETS = ("mysql", "tsql", "snowflake", "bigquery", "postgres", "ansi")


def pretty_sql(sql: str, dialect: Optional[str] = None) -> str:
    if not (sql or "").strip():
        return sql
    try:
        import sqlglot
        out = sqlglot.transpile(sql, read=dialect or "postgres", pretty=True)
        return out[0] if out else sql
    except Exception:
        return sql


def transpile_sql(
    sql: str,
    source: Optional[str] = None,
    target: Optional[str] = None,
    targets: Optional[Sequence[str]] = None,
) -> Dict[str, str]:
    """Converte SQL para um ou vários dialetos. Falhas individuais são omitidas."""
    result: Dict[str, str] = {}
    if not (sql or "").strip():
        return result
    try:
        import sqlglot
    except Exception:
        return result

    wanted = [target] if target else list(targets or DEFAULT_TARGETS)
    for dest in wanted:
        if not dest:
            continue
        try:
            out = sqlglot.transpile(sql, read=source or "postgres", write=dest, pretty=True)
            if out:
                result[dest] = out[0]
        except Exception:
            continue
    return result
