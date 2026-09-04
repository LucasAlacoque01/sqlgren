"""Rastreio multi-hop e delta de PR — o que o SQLPrism cobra caro, sem DuckDB."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


def _index(blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_id = {b.get("id"): b for b in blocks}
    writers: Dict[str, List[str]] = {}
    readers: Dict[str, List[str]] = {}
    for block in blocks:
        qid = block.get("id")
        written = {t.lower() for t in (block.get("tabelas_escrita") or [])}
        for table in block.get("tabelas") or []:
            key = table.lower()
            if key in written:
                writers.setdefault(key, []).append(qid)
            else:
                readers.setdefault(key, []).append(qid)
    return {"by_id": by_id, "writers": writers, "readers": readers}


def cascade_from_table(table: str, blocks: List[Dict[str, Any]], depth: int = 3) -> Dict[str, Any]:
    """Se a tabela mudar: leitores (hop 1), tabelas que eles escrevem (hop 2), leitores seguintes (hop 3)."""
    idx = _index(blocks)
    start = (table or "").lower()
    hop1_ids = list(dict.fromkeys(idx["readers"].get(start, [])))
    written_next: List[str] = []
    hop2_ids: List[str] = []
    for qid in hop1_ids:
        q = idx["by_id"].get(qid) or {}
        for dest in q.get("tabelas_escrita") or []:
            dest_l = dest.lower()
            if dest_l == start:
                continue
            written_next.append(dest_l)
            hop2_ids.extend(idx["readers"].get(dest_l, []))
    hop2_ids = [i for i in dict.fromkeys(hop2_ids) if i not in set(hop1_ids)]
    hops = []
    if hop1_ids:
        hops.append({
            "hop": 1,
            "rotulo": "Lê esta tabela",
            "queries": [_brief(idx["by_id"].get(i) or {"id": i}) for i in hop1_ids[:20]],
        })
    if written_next:
        hops.append({
            "hop": 2,
            "rotulo": "Tabelas que esses leitores escrevem",
            "tabelas": list(dict.fromkeys(written_next))[:16],
        })
    if hop2_ids and depth >= 3:
        hops.append({
            "hop": 3,
            "rotulo": "Lê o que o hop 1 escreveu",
            "queries": [_brief(idx["by_id"].get(i) or {"id": i}) for i in hop2_ids[:20]],
        })
    return {
        "tabela": start,
        "alcance": len(hop1_ids) + len(hop2_ids),
        "hops": hops,
    }


def attach_cascades(impact: List[Dict[str, Any]], blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for row in impact:
        row["cascata"] = cascade_from_table(row.get("tabela") or "", blocks)
    return impact


def _brief(block: Dict[str, Any]) -> Dict[str, str]:
    return {
        "id": block.get("id") or "",
        "titulo": block.get("titulo") or "",
        "arquivo": block.get("arquivo") or "",
        "tipo": block.get("tipo") or "",
    }


def diff_against_baseline(blocks: List[Dict[str, Any]], baseline_path: Optional[Path]) -> Dict[str, Any]:
    """Compara hashes/arquivos com um catalogo.json anterior (impacto de PR)."""
    empty = {"added": [], "removed": [], "changed": [], "unchanged": 0, "tables_touched": [], "impacted": []}
    if not baseline_path:
        return empty
    path = Path(baseline_path)
    if not path.exists():
        return {**empty, "erro": f"baseline inexistente: {path}"}
    try:
        previous = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {**empty, "erro": str(exc)}

    old_by_file = {
        (q.get("arquivo") or ""): q
        for q in (previous.get("queries") or [])
        if q.get("arquivo")
    }
    new_by_file = { (b.get("arquivo") or ""): b for b in blocks if b.get("arquivo") }

    added, removed, changed = [], [], []
    for arquivo, block in new_by_file.items():
        old = old_by_file.get(arquivo)
        if old is None:
            added.append(_brief(block))
        elif (old.get("hash") or "") != (block.get("hash") or ""):
            changed.append(_brief(block))
    for arquivo, old in old_by_file.items():
        if arquivo not in new_by_file:
            removed.append(_brief(old))

    touched: Set[str] = set()
    seed_ids = {row["id"] for row in added + changed}
    for block in blocks:
        if block.get("id") in seed_ids:
            touched.update(t.lower() for t in (block.get("tabelas") or []))

    impacted = []
    seen = set(seed_ids)
    for block in blocks:
        if block.get("id") in seen:
            continue
        if touched & {t.lower() for t in (block.get("tabelas") or [])}:
            impacted.append(_brief(block))
            seen.add(block.get("id"))

    extra = []
    for table in list(touched)[:24]:
        casc = cascade_from_table(table, blocks)
        for hop in casc.get("hops") or []:
            for q in hop.get("queries") or []:
                if q.get("id") and q["id"] not in seen:
                    extra.append(q)
                    seen.add(q["id"])
    impacted.extend(extra[:24])

    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "unchanged": max(0, len(new_by_file) - len(added) - len(changed)),
        "tables_touched": sorted(touched),
        "impacted": impacted[:40],
    }


def ask_catalog(catalog: Dict[str, Any], query: str) -> List[Dict[str, Any]]:
    """Filtro estrutural: table: col: tag: tipo: + texto."""
    raw = (query or "").strip()
    tables, cols, tags, types, text = [], [], [], [], []
    for part in raw.split():
        if ":" in part:
            key, _, val = part.partition(":")
            key, val = key.lower(), val.lower()
            if key in {"table", "tabela"}:
                tables.append(val)
            elif key == "col":
                cols.append(val)
            elif key == "tag":
                tags.append(val)
            elif key in {"tipo", "type"}:
                types.append(val)
            else:
                text.append(part.lower())
        else:
            text.append(part.lower())

    hits = []
    for q in catalog.get("queries") or []:
        if tables and not all(any(t in x.lower() for x in (q.get("tabelas") or [])) for t in tables):
            continue
        colspace = [*(q.get("colunas") or []), *sum((q.get("uso_colunas") or {}).values(), [])]
        if cols and not all(any(c in str(x).lower() for x in colspace) for c in cols):
            continue
        if tags and not all(any(t in str(x).lower() for x in (q.get("tags") or [])) for t in tags):
            continue
        if types and not all(t in str(q.get("tipo") or "").lower() for t in types):
            continue
        hay = " ".join([
            q.get("titulo") or "",
            q.get("descricao") or "",
            q.get("arquivo") or "",
            q.get("sql") or "",
            " ".join(q.get("tabelas") or []),
        ]).lower()
        if text and not all(term in hay for term in text):
            continue
        hits.append(q)
    return hits
