"""Relações implícitas por nome de coluna — SchemaSpy sem JDBC."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Dict, List, Set

_KEYISH = re.compile(r"^(co_|nu_|id_|fk_|cd_|pk_)", re.I)
_SKIP = {
    "id", "nome", "name", "descricao", "descrição", "status", "tipo", "data",
    "ano", "mes", "mês", "dia", "valor", "qtd", "count", "total", "flag",
}


def _bare(col: str) -> str:
    text = str(col or "").strip().strip('"').strip("'")
    if "." in text:
        text = text.split(".")[-1]
    return text.lower()


def _tables_of(block: Dict[str, Any]) -> List[str]:
    return [str(t).lower() for t in (block.get("tabelas") or []) if t]


def _columns_of(block: Dict[str, Any]) -> List[str]:
    names: List[str] = []
    names.extend(block.get("colunas") or [])
    for cols in (block.get("uso_colunas") or {}).values():
        names.extend(cols or [])
    for row in block.get("column_lineage") or []:
        names.append(row.get("coluna") or "")
        for origin in row.get("origens") or []:
            names.append(str(origin).split(".")[-1] if "." in str(origin) else str(origin))
    return names


def build_implied_keys(blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Colunas-chave que aparecem em 2+ tabelas — FK lógica sem schema."""
    col_tables: Dict[str, Set[str]] = defaultdict(set)
    col_queries: Dict[str, List[str]] = defaultdict(list)
    for block in blocks:
        tables = _tables_of(block)
        if len(tables) < 1:
            continue
        seen_in_block: Set[str] = set()
        for raw in _columns_of(block):
            bare = _bare(raw)
            if not bare or bare in _SKIP or len(bare) < 3:
                continue
            if not _KEYISH.match(bare) and not bare.endswith("_id") and not bare.endswith("_pk"):
                continue
            for table in tables:
                col_tables[bare].add(table)
            if block.get("id") not in seen_in_block:
                col_queries[bare].append(block.get("id") or "")
                seen_in_block.add(bare)

    rows: List[Dict[str, Any]] = []
    for col, tables in col_tables.items():
        if len(tables) < 2:
            continue
        rows.append({
            "coluna": col,
            "tabelas": sorted(tables),
            "juntas": len(tables),
            "queries": [q for q in col_queries.get(col, []) if q][:16],
            "evidencia": "mesmo nome de chave em tabelas distintas (SchemaSpy implied, sem JDBC)",
        })
    rows.sort(key=lambda r: (-r["juntas"], -len(r["queries"]), r["coluna"]))
    return rows[:80]
