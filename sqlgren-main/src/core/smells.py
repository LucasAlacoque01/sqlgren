"""Cheiros estruturais extras (SQLFluff-lite) — só o que dá para ver sem banco."""

from __future__ import annotations

import re
from typing import Any, Dict, List

from .i18n import msg, normalize_locale


def extra_smells(info: Dict[str, Any], sql: str, locale: str = "pt") -> List[Dict[str, str]]:
    locale = normalize_locale(locale)
    out: List[Dict[str, str]] = []
    tipo = info.get("tipo")
    ctes = [str(c) for c in (info.get("ctes") or []) if c]

    if tipo == "INSERT" and re.search(r"INSERT\s+INTO\s+[\w.]+\s+SELECT\b", sql, re.I):
        out.append({
            "nivel": "alerta",
            "codigo": "insert-no-columns",
            "mensagem": msg("insert-no-columns", locale),
        })

    unused = []
    for cte in ctes:
        hits = len(re.findall(rf"\b{re.escape(cte)}\b", sql, re.I))
        if hits <= 1:
            unused.append(cte)
    if unused:
        out.append({
            "nivel": "alerta",
            "codigo": "unused-cte",
            "mensagem": msg("unused-cte", locale, names=", ".join(unused[:4])),
        })

    bare_joins = re.findall(
        r"\b(?:INNER\s+|LEFT\s+|RIGHT\s+|FULL\s+)?JOIN\s+[\w.]+(?:\s+(?!ON\b|JOIN\b|WHERE\b|LEFT\b|RIGHT\b|FULL\b|INNER\b|CROSS\b)[\w]+)?\s*(?:,|WHERE|GROUP|ORDER|LIMIT|;|$)",
        sql,
        re.I,
    )
    has_on_less = bool(re.search(r"\bJOIN\s+[\w.]+(?:\s+\w+)?\s+(?:WHERE|GROUP|ORDER|LIMIT|;|$)", sql, re.I))
    if has_on_less and not re.search(r"\bCROSS\s+JOIN\b", sql, re.I):
        out.append({
            "nivel": "critico",
            "codigo": "join-without-on",
            "mensagem": msg("join-without-on", locale),
        })
    elif bare_joins and "ON" not in sql.upper() and not re.search(r"\bCROSS\s+JOIN\b", sql, re.I):
        if info.get("joins_count", 0) and not info.get("join_implicito"):
            out.append({
                "nivel": "alerta",
                "codigo": "join-on-missing",
                "mensagem": msg("join-on-missing", locale),
            })

    if re.search(r"\bNOT\s+IN\s*\(\s*SELECT\b", sql, re.I):
        out.append({
            "nivel": "alerta",
            "codigo": "not-in-subquery",
            "mensagem": msg("not-in-subquery", locale),
        })

    if info.get("distinct") and info.get("joins_count", 0) >= 1:
        out.append({
            "nivel": "info",
            "codigo": "distinct-join-fanout",
            "mensagem": msg("distinct-join-fanout", locale),
        })

    if re.search(r"\bUNION\b", sql, re.I) and not re.search(r"\bUNION\s+ALL\b", sql, re.I):
        out.append({
            "nivel": "info",
            "codigo": "union-dedup",
            "mensagem": msg("union-dedup", locale),
        })

    if re.search(r"\bCROSS\s+JOIN\b", sql, re.I):
        out.append({
            "nivel": "alerta",
            "codigo": "cross-join",
            "mensagem": msg("cross-join", locale),
        })

    return out
