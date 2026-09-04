"""Monta o catálogo canônico a partir dos blocos analisados."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List

from .cascade import attach_cascades, diff_against_baseline
from .i18n import normalize_locale, pitch
from .implied import build_implied_keys
from .redact import redact_catalog
from .intelligence import (
    build_anomalies,
    build_briefing,
    build_columns,
    build_impact,
    build_relations,
    compute_health,
    find_twins,
    mermaid_lineage,
    _graph_metrics,
)

try:
    from src import __version__
except ImportError:
    __version__ = "6.0.0"


def _folder(arquivo: str) -> str:
    if "/" in arquivo:
        return arquivo.rsplit("/", 1)[0]
    if "\\" in arquivo:
        return arquivo.rsplit("\\", 1)[0]
    return "raiz"


def build_catalog(
    blocks: List[Dict[str, Any]],
    title: str,
    lineage: Dict[str, Any],
    run: Dict[str, Any],
) -> Dict[str, Any]:
    tipos = Counter(b.get("tipo") for b in blocks)
    semantic = Counter(b.get("tipo_semantico") for b in blocks)
    complexidades = Counter(b.get("complexidade") for b in blocks)
    dominios = Counter(b.get("dominio") for b in blocks)
    pastas = Counter(_folder(b.get("arquivo", "")) for b in blocks)

    all_tables = {t for b in blocks for t in b.get("tabelas", [])}
    alerts = sum(1 for b in blocks for i in b.get("insights", []) if i.get("nivel") in {"alerta", "critico"})
    criticos = sum(1 for b in blocks for i in b.get("insights", []) if i.get("nivel") == "critico")
    with_cte = sum(1 for b in blocks if b.get("ctes"))
    heavy = sum(1 for b in blocks if b.get("complexidade") == "Alta")
    pii_n = sum(1 for b in blocks if (b.get("pii") or {}).get("exposto"))
    missing_docs = sum(1 for b in blocks if not b.get("tem_header"))

    coverage = 100.0
    if blocks:
        documented = sum(1 for b in blocks if b.get("descricao") and b.get("tabelas"))
        coverage = round(100 * documented / len(blocks), 1)

    locale = normalize_locale(run.get("locale"))
    twins = find_twins(blocks, locale=locale)
    impact = attach_cascades(build_impact(blocks, lineage.get("tables") or []), blocks)
    implied_keys = build_implied_keys(blocks)
    delta = diff_against_baseline(blocks, run.get("baseline"))
    graph = _graph_metrics(lineage.get("tables") or [], blocks)

    stats = {
        "queries": len(blocks),
        "tabelas": len(all_tables),
        "pastas": len(pastas),
        "dominios": len(dominios),
        "joins": sum(b.get("joins_count", 0) for b in blocks),
        "ctes": sum(len(b.get("ctes") or []) for b in blocks),
        "linhas": sum(b.get("linhas", 0) for b in blocks),
        "alertas": alerts,
        "criticos": criticos,
        "com_cte": with_cte,
        "complexas": heavy,
        "cobertura": coverage,
        "saude": 0,
        "gemeos": sum(1 for t in twins if t.get("kind") == "gemeo"),
        "parecidos": len(twins),
        "hubs": sum(1 for row in impact if row.get("raio", 0) >= 2),
        "pii": pii_n,
        "sem_header": missing_docs,
        "heuristicas": sum(1 for b in blocks if b.get("parse_mode") == "heuristic"),
        "implied": len(implied_keys),
        "changed": len(delta.get("changed") or []) + len(delta.get("added") or []),
    }
    stats["saude"] = compute_health(blocks, run, criticos, alerts, coverage)
    briefing = build_briefing(blocks, stats, twins, impact, locale=locale)
    columns = build_columns(blocks)
    relations = build_relations(blocks)
    anomalies = build_anomalies(blocks, lineage.get("tables") or [], locale=locale)
    mermaid = mermaid_lineage(lineage.get("tables") or [], blocks)
    stats["colunas"] = len(columns)
    stats["relacoes"] = len(relations)

    catalog = {
        "meta": {
            "title": title,
            "product": "Acervo",
            "version": __version__,
            "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "dialect_default": run.get("dialect") or "auto",
            "target_dialect": run.get("target_dialect"),
            "locale": locale,
            "redacted": bool(run.get("redact_pii")),
            "shareable": bool(run.get("redact_pii")),
            "edition": "community",
            "pitch": pitch(locale),
        },
        "run": run,
        "stats": stats,
        "distribuicao": {
            "tipo": dict(tipos),
            "semantico": dict(semantic),
            "complexidade": dict(complexidades),
            "dominio": dict(dominios),
            "pasta": dict(pastas),
        },
        "lineage": lineage,
        "graph": graph,
        "twins": twins,
        "impact": impact,
        "briefing": briefing,
        "columns": columns,
        "relations": relations,
        "anomalies": anomalies,
        "implied_keys": implied_keys,
        "delta": delta,
        "mermaid": mermaid,
        "queries": blocks,
    }
    if run.get("redact_pii"):
        catalog = redact_catalog(catalog)
    return catalog
