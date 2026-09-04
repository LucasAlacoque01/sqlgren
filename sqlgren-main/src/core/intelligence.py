"""Gêmeos, blast radius, métricas de grafo, saúde do catálogo e briefing."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Set, Tuple

from .i18n import briefing_copy, msg, normalize_locale


def _norm(items: List[str]) -> Set[str]:
    return {str(i).lower().strip() for i in (items or []) if i}


def _tokens(sql: str) -> Set[str]:
    clean = re.sub(r"--.*?$", "", sql or "", flags=re.M)
    return set(re.findall(r"[a-z_][a-z0-9_]*", clean.lower()))


def _jaccard(a: Set[str], b: Set[str]) -> float:
    if not a and not b:
        return 0.0
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def find_twins(blocks: List[Dict[str, Any]], threshold: float = 0.42, locale: str = "pt") -> List[Dict[str, Any]]:
    pairs: List[Dict[str, Any]] = []
    for i, left in enumerate(blocks):
        for right in blocks[i + 1 :]:
            tables_a = _norm(left.get("tabelas", []))
            tables_b = _norm(right.get("tabelas", []))
            table_score = _jaccard(tables_a, tables_b)
            metric_score = _jaccard(_norm(left.get("metricas", [])), _norm(right.get("metricas", [])))
            token_score = _jaccard(_tokens(left.get("sql", "")), _tokens(right.get("sql", "")))
            domain_bonus = 0.08 if left.get("dominio") and left.get("dominio") == right.get("dominio") else 0.0
            score = min(1.0, table_score * 0.5 + metric_score * 0.2 + token_score * 0.3 + domain_bonus)
            if score < threshold:
                continue
            overlap = sorted(tables_a & tables_b)
            pairs.append({
                "a": left.get("id"),
                "b": right.get("id"),
                "titulo_a": left.get("titulo"),
                "titulo_b": right.get("titulo"),
                "arquivo_a": left.get("arquivo"),
                "arquivo_b": right.get("arquivo"),
                "score": round(score * 100),
                "overlap": overlap,
                "kind": "gemeo" if score >= 0.75 else "parecido",
                "economia": msg("twin.duplicate" if score >= 0.75 else "twin.review", locale),
            })
    pairs.sort(key=lambda p: p["score"], reverse=True)
    return pairs[:24]


def _graph_metrics(tables: List[Dict[str, Any]], blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Centralidade (hubs/authorities/bridges). Usa NetworkX se disponível."""
    nodes = [f"tbl:{(t.get('nome') or '').lower()}" for t in tables] + [b.get("id") for b in blocks]
    edges: List[Tuple[str, str]] = []
    for block in blocks:
        qid = block.get("id")
        written = {x.lower() for x in (block.get("tabelas_escrita") or [])}
        for table in block.get("tabelas") or []:
            tid = f"tbl:{table.lower()}"
            if table.lower() in written:
                edges.append((qid, tid))
            else:
                edges.append((tid, qid))

    degree: Dict[str, float] = {n: 0.0 for n in nodes}
    for src, dst in edges:
        if src in degree:
            degree[src] += 1
        if dst in degree:
            degree[dst] += 1
    n = max(1, len(nodes) - 1)
    degree_cent = {k: round(v / n, 4) for k, v in degree.items()}

    betweenness: Dict[str, float] = {k: 0.0 for k in nodes}
    authority: Dict[str, float] = {k: 0.0 for k in nodes}
    engine = "builtin"

    try:
        import networkx as nx  # type: ignore

        graph = nx.DiGraph()
        graph.add_nodes_from(nodes)
        graph.add_edges_from(edges)
        degree_cent = {k: round(v, 4) for k, v in nx.degree_centrality(graph).items()}
        betweenness = {k: round(v, 4) for k, v in nx.betweenness_centrality(graph).items()}
        try:
            hubs, auths = nx.hits(graph, max_iter=200, tol=1e-6)
            authority = {k: round(v, 4) for k, v in auths.items()}
            hub_scores = {k: round(v, 4) for k, v in hubs.items()}
        except Exception:
            hub_scores = degree_cent
            in_deg = dict(graph.in_degree())
            mx = max(list(in_deg.values()) or [1]) or 1
            authority = {k: round(v / mx, 4) for k, v in in_deg.items()}
        engine = "networkx"
    except Exception:
        hub_scores = degree_cent
        in_count: Dict[str, int] = {n: 0 for n in nodes}
        for _, dst in edges:
            if dst in in_count:
                in_count[dst] += 1
        mx = max(list(in_count.values()) or [1]) or 1
        authority = {k: round(v / mx, 4) for k, v in in_count.items()}
        betweenness = {k: round(degree_cent.get(k, 0) * 0.5, 4) for k in nodes}

    def top(mapping: Dict[str, float], prefix: str, k: int = 8) -> List[Dict[str, Any]]:
        ranked = sorted(
            ((name, score) for name, score in mapping.items() if name.startswith(prefix)),
            key=lambda kv: kv[1],
            reverse=True,
        )
        return [{"id": name, "score": score} for name, score in ranked[:k] if score > 0]

    bridges = [row for row in top(betweenness, "tbl:", 8) if row["score"] > 0]
    return {
        "degree": degree_cent,
        "betweenness": betweenness,
        "authority": authority,
        "hubs": top(hub_scores, "tbl:", 10),
        "authorities": top(authority, "tbl:", 10),
        "bridges": bridges,
        "engine": engine,
    }


def build_impact(blocks: List[Dict[str, Any]], tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_id = {b.get("id"): b for b in blocks}
    impact = []
    for table in tables:
        qs = [by_id[qid] for qid in table.get("queries", []) if qid in by_id]
        mutations = [q for q in qs if q.get("tipo") in {"INSERT", "UPDATE", "DELETE", "MERGE"}]
        writers = [q for q in qs if table.get("nome", "").lower() in {t.lower() for t in (q.get("tabelas_escrita") or [])}]
        if not writers:
            writers = mutations
        writer_ids = {q.get("id") for q in writers}
        impacted = [
            q for q in qs
            if q.get("id") not in writer_ids
            and table.get("nome", "").lower() in {t.lower() for t in (q.get("tabelas_leitura") or q.get("tabelas") or [])}
        ]
        if writers:
            risco = "alto"
        elif len(qs) >= 3:
            risco = "medio"
        else:
            risco = "baixo"
        vizinhos: Set[str] = set()
        for q in qs:
            vizinhos.update(_norm(q.get("tabelas", [])))
        vizinhos.discard((table.get("nome") or "").lower())
        impact.append({
            "tabela": table.get("nome"),
            "uso": table.get("uso"),
            "queries": table.get("queries", []),
            "titulos": [q.get("titulo") for q in qs],
            "risco": risco,
            "mutacoes": len(mutations),
            "raio": len(qs),
            "vizinhos": sorted(vizinhos)[:12],
            "escritores": [q.get("id") for q in writers],
            "impactados": [
                {"id": q.get("id"), "titulo": q.get("titulo"), "arquivo": q.get("arquivo")}
                for q in impacted
            ],
        })
    impact.sort(key=lambda row: (-row["raio"], row["tabela"] or ""))
    return impact


def compute_health(
    blocks: List[Dict[str, Any]],
    run: Dict[str, Any],
    criticos: int,
    alerts: int,
    coverage: float,
) -> float:
    pii_n = sum(1 for b in blocks if (b.get("pii") or {}).get("exposto"))
    pii_penalty = min(25, pii_n * 5)
    documented = sum(1 for b in blocks if b.get("tem_header") or (b.get("comentario") or "").strip())
    docs = round(100 * documented / len(blocks), 1) if blocks else 100.0
    parse_ok = 100.0 if run.get("failed", 0) == 0 else max(40.0, 100 - run.get("failed", 0) * 15)
    heuristic = sum(1 for b in blocks if b.get("parse_mode") == "heuristic")
    parse_ok = max(40.0, parse_ok - heuristic * 8)
    health = (
        coverage * 0.30
        + docs * 0.15
        + (100 - min(40, criticos * 20)) * 0.25
        + (100 - min(30, alerts * 4)) * 0.10
        + parse_ok * 0.10
        + (100 - pii_penalty) * 0.10
    )
    return max(0, min(100, round(health, 1)))


def build_briefing(
    blocks: List[Dict[str, Any]],
    stats: Dict[str, Any],
    twins: List[Dict[str, Any]],
    impact: List[Dict[str, Any]],
    locale: str = "pt",
) -> Dict[str, Any]:
    criticos = [b for b in blocks for i in b.get("insights", []) if i.get("nivel") == "critico"]
    hubs = [row for row in impact if row.get("raio", 0) >= 2][:5]
    gemeos = [t for t in twins if t.get("kind") == "gemeo"]
    copy = briefing_copy(locale, stats, twins, len(hubs))
    return {
        **copy,
        "hubs": hubs,
        "gemeos": gemeos[:5] or twins[:5],
        "criticos": len(criticos),
    }


def build_columns(blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    for block in blocks:
        uso = block.get("uso_colunas") or {}
        for clause, cols in uso.items():
            for col in cols:
                key = col.lower()
                slot = index.setdefault(
                    key,
                    {"nome": col, "select": 0, "where": 0, "join": 0, "group": 0, "order": 0, "having": 0, "queries": [], "pii": False},
                )
                slot[clause] = slot.get(clause, 0) + 1
                if block.get("id") not in slot["queries"]:
                    slot["queries"].append(block.get("id"))
        for col in block.get("colunas") or []:
            key = str(col).lower()
            slot = index.setdefault(
                key,
                {"nome": col, "select": 0, "where": 0, "join": 0, "group": 0, "order": 0, "having": 0, "queries": [], "pii": False},
            )
            slot["select"] += 1
            if block.get("id") not in slot["queries"]:
                slot["queries"].append(block.get("id"))
        for hit in (block.get("pii") or {}).get("hits") or []:
            key = str(hit.get("coluna") or "").lower()
            if key in index:
                index[key]["pii"] = True
    rows = list(index.values())
    rows.sort(key=lambda r: (-len(r["queries"]), r["nome"].lower()))
    return rows[:200]


def build_relations(blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    pair_count: Dict[tuple, int] = {}
    pair_queries: Dict[tuple, List[str]] = {}
    for block in blocks:
        tables = sorted(_norm(block.get("tabelas", [])))
        for i, left in enumerate(tables):
            for right in tables[i + 1 :]:
                key = (left, right)
                pair_count[key] = pair_count.get(key, 0) + 1
                pair_queries.setdefault(key, []).append(block.get("id"))
    relations = [
        {"a": a, "b": b, "juntos": n, "queries": pair_queries[(a, b)]}
        for (a, b), n in pair_count.items()
        if n >= 1
    ]
    relations.sort(key=lambda r: (-r["juntos"], r["a"]))
    return relations[:80]


def build_anomalies(
    blocks: List[Dict[str, Any]],
    tables: List[Dict[str, Any]],
    locale: str = "pt",
) -> List[Dict[str, str]]:
    locale = normalize_locale(locale)
    out: List[Dict[str, str]] = []
    orphans = [t for t in tables if t.get("uso", 0) == 1]
    if orphans:
        out.append({"nivel": "info", "codigo": "tabela-unica", "mensagem": msg("tabela-unica", locale, n=len(orphans))})
    isolated = [b for b in blocks if not b.get("tabelas")]
    if isolated:
        out.append({"nivel": "info", "codigo": "query-sem-tabela", "mensagem": msg("query-sem-tabela", locale, n=len(isolated))})
    implicit = [b for b in blocks if b.get("join_implicito")]
    if implicit:
        out.append({"nivel": "alerta", "codigo": "comma-join-catalog", "mensagem": msg("comma-join-catalog", locale, n=len(implicit))})
    pii_n = sum(1 for b in blocks if (b.get("pii") or {}).get("exposto"))
    if pii_n:
        out.append({"nivel": "alerta", "codigo": "pii-catalog", "mensagem": msg("pii-catalog", locale, n=pii_n)})
    missing = [b for b in blocks if not b.get("tem_header")]
    if missing:
        out.append({"nivel": "alerta", "codigo": "undocumented", "mensagem": msg("undocumented", locale, n=len(missing))})
    return out


def mermaid_lineage(tables: List[Dict[str, Any]], blocks: List[Dict[str, Any]]) -> str:
    lines = ["flowchart LR"]
    for table in tables[:30]:
        nid = re.sub(r"[^A-Za-z0-9_]", "_", table.get("nome") or "t")
        lines.append(f'  {nid}["{table.get("nome")}"]')
    for block in blocks[:40]:
        qid = re.sub(r"[^A-Za-z0-9_]", "_", block.get("id") or "q")
        label = (block.get("titulo") or block.get("id") or "")[:36]
        lines.append(f'  {qid}("{label}")')
        for table in block.get("tabelas") or []:
            nid = re.sub(r"[^A-Za-z0-9_]", "_", table)
            lines.append(f"  {nid} --> {qid}")
    return "\n".join(lines)


def schema_impact_markdown(catalog: Dict[str, Any]) -> str:
    locale = normalize_locale((catalog.get("meta") or {}).get("locale"))
    en = locale == "en"
    stats = catalog.get("stats") or {}
    impact = catalog.get("impact") or []
    twins = catalog.get("twins") or []
    criticos = [
        (q, i)
        for q in catalog.get("queries") or []
        for i in q.get("insights") or []
        if i.get("nivel") == "critico"
    ]
    lines = [
        "## Acervo — schema impact" if en else "## Acervo — impacto de schema",
        "",
        f"- Queries: **{stats.get('queries', 0)}** · Tables: **{stats.get('tabelas', 0)}** · Health: **{stats.get('saude', 0)}**"
        if en else
        f"- Queries: **{stats.get('queries', 0)}** · Tabelas: **{stats.get('tabelas', 0)}** · Saúde: **{stats.get('saude', 0)}**",
        f"- Critical: **{stats.get('criticos', 0)}** · PII: **{stats.get('pii', 0)}** · Twins: **{stats.get('gemeos', 0)}**"
        if en else
        f"- Críticos: **{stats.get('criticos', 0)}** · PII: **{stats.get('pii', 0)}** · Gêmeos: **{stats.get('gemeos', 0)}**",
        "",
        "### Hubs",
        "",
    ]
    for row in impact[:8]:
        if en:
            lines.append(f"- `{row.get('tabela')}` — radius {row.get('raio')} · risk {row.get('risco')} · mutations {row.get('mutacoes')}")
        else:
            lines.append(f"- `{row.get('tabela')}` — raio {row.get('raio')} · risco {row.get('risco')} · mutações {row.get('mutacoes')}")
    if not impact:
        lines.append("- No hubs." if en else "- Nenhum hub.")
    lines += ["", "### Critical" if en else "### Críticos", ""]
    if criticos:
        for q, ins in criticos[:12]:
            lines.append(f"- `{q.get('arquivo')}` — {ins.get('mensagem')}")
    else:
        lines.append("- No structural criticals." if en else "- Nenhum crítico estrutural.")
    lines += ["", "### Twins" if en else "### Gêmeos", ""]
    if twins:
        for pair in twins[:8]:
            lines.append(f"- {pair.get('score')}% · {pair.get('titulo_a')} ↔ {pair.get('titulo_b')}")
    else:
        lines.append("- No similar pairs." if en else "- Nenhum par semelhante.")
    delta = catalog.get("delta") or {}
    if delta.get("changed") or delta.get("added") or delta.get("removed"):
        lines += ["", "### PR delta (vs baseline)" if en else "### Delta do PR (vs baseline)", ""]
        if delta.get("changed"):
            lines.append("Changed:" if en else "Alteradas:")
            for row in delta["changed"][:12]:
                lines.append(f"- `{row.get('arquivo')}` — {row.get('titulo')}")
        if delta.get("added"):
            lines.append("Added:" if en else "Novas:")
            for row in delta["added"][:8]:
                lines.append(f"- `{row.get('arquivo')}`")
        if delta.get("removed"):
            lines.append("Removed:" if en else "Removidas:")
            for row in delta["removed"][:8]:
                lines.append(f"- `{row.get('arquivo')}`")
        if delta.get("tables_touched"):
            label = "Tables touched: " if en else "Tabelas tocadas: "
            lines.append(label + ", ".join(f"`{t}`" for t in delta["tables_touched"][:16]))
        if delta.get("impacted"):
            lines.append("Queries in the blast radius (includes cascade):" if en else "Consultas no raio (inclui cascata):")
            for row in delta["impacted"][:16]:
                lines.append(f"- `{row.get('arquivo')}` — {row.get('titulo')}")
    implied = catalog.get("implied_keys") or []
    if implied:
        lines += ["", "### Implied keys (SchemaSpy without a database)" if en else "### Chaves implícitas (SchemaSpy sem banco)", ""]
        for row in implied[:8]:
            lines.append(f"- `{row.get('coluna')}` em {', '.join(f'`{t}`' for t in (row.get('tabelas') or [])[:6])}")
    lines.append("")
    return "\n".join(lines)
