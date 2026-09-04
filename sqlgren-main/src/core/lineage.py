"""Grafo de dependências tabela ↔ query e linhagem de colunas agregada."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Set


def build_lineage(blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
    table_to_queries: Dict[str, List[str]] = defaultdict(list)
    writers: Dict[str, List[str]] = defaultdict(list)
    readers: Dict[str, List[str]] = defaultdict(list)
    query_nodes: List[Dict[str, Any]] = []
    table_nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, str]] = []
    seen_tables: Set[str] = set()

    for block in blocks:
        qid = block["id"]
        query_nodes.append({
            "id": qid,
            "kind": "query",
            "label": block.get("titulo") or qid,
            "tipo": block.get("tipo"),
            "complexidade": block.get("complexidade"),
            "dominio": block.get("dominio"),
        })
        written = {t.lower() for t in (block.get("tabelas_escrita") or [])}
        for table in block.get("tabelas", []):
            table_id = f"tbl:{table.lower()}"
            table_to_queries[table].append(qid)
            rel = "writes" if table.lower() in written else "feeds"
            edges.append({"source": table_id, "target": qid, "rel": rel})
            if table.lower() in written:
                writers[table.lower()].append(qid)
            else:
                readers[table.lower()].append(qid)
            if table.lower() not in seen_tables:
                seen_tables.add(table.lower())
                table_nodes.append({"id": table_id, "kind": "table", "label": table})

    tables = []
    for name, qids in sorted(table_to_queries.items(), key=lambda kv: (-len(kv[1]), kv[0].lower())):
        key = name.lower()
        tables.append({
            "nome": name,
            "id": f"tbl:{key}",
            "uso": len(qids),
            "queries": qids,
            "escritores": writers.get(key, []),
            "leitores": readers.get(key, []),
        })

    hubs = [t for t in tables if t["uso"] > 1]
    isolated = [b["id"] for b in blocks if not b.get("tabelas")]

    column_edges: List[Dict[str, str]] = []
    for block in blocks:
        for row in block.get("column_lineage") or []:
            target = row.get("coluna") or ""
            for origin in row.get("origens") or []:
                column_edges.append({
                    "query": block.get("id"),
                    "source": origin,
                    "target": target,
                })

    return {
        "nodes": table_nodes + query_nodes,
        "edges": edges,
        "tables": tables,
        "hubs": hubs[:12],
        "isolated": isolated,
        "column_edges": column_edges[:400],
    }
