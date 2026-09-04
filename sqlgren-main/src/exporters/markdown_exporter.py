"""CATALOGO.md, BRIEFING.md e comentário de PR."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

try:
    from ..core.intelligence import schema_impact_markdown
except ImportError:
    from core.intelligence import schema_impact_markdown


def exportar_markdown(catalog: Dict[str, Any], output_dir: Path, filename: str = "CATALOGO.md") -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / filename
    meta = catalog.get("meta", {})
    stats = catalog.get("stats", {})
    blocks = catalog.get("queries", [])

    locale = str(meta.get("locale") or "pt").lower()
    en = locale.startswith("en")
    lines = [
        f"# {meta.get('title', 'Acervo')}",
        "",
        f"{'Generated at' if en else 'Gerado em'} `{meta.get('generated_at', '')}` · Acervo {meta.get('version', '')}"
        + (" · PII redacted" if meta.get("redacted") else ""),
        "",
        "## Overview" if en else "## Panorama",
        "",
        f"- Queries: **{stats.get('queries', 0)}**",
        f"- {'Tables' if en else 'Tabelas'}: **{stats.get('tabelas', 0)}**",
        f"- {'Catalog health' if en else 'Saúde do catálogo'}: **{stats.get('saude', 0)}**",
        f"- {'Structural coverage' if en else 'Cobertura estrutural'}: **{stats.get('cobertura', 0)}%**",
        f"- {'Alerts' if en else 'Alertas'}: **{stats.get('alertas', 0)}** · {'Critical' if en else 'Críticos'}: **{stats.get('criticos', 0)}**",
        f"- PII: **{stats.get('pii', 0)}** · {'Twins' if en else 'Gêmeos'}: **{stats.get('gemeos', 0)}**",
        "",
        "## Index" if en else "## Índice",
        "",
    ]

    for b in blocks:
        lines.append(
            f"- [`{b.get('id')}`](#{b.get('id')}) {b.get('titulo')} — {b.get('tipo')} · {b.get('complexidade')}"
        )

    lines.append("")

    for b in blocks:
        lines.extend([
            f"## {b.get('titulo')} {{#{b.get('id')}}}",
            "",
            f"{b.get('descricao')}",
            "",
            f"| {'Field' if en else 'Campo'} | {'Value' if en else 'Valor'} |",
            f"| --- | --- |",
            f"| {'File' if en else 'Arquivo'} | `{b.get('arquivo')}` |",
            f"| {'Type' if en else 'Tipo'} | {b.get('tipo')} / {b.get('tipo_semantico')} |",
            f"| {'Complexity' if en else 'Complexidade'} | {b.get('complexidade')} ({b.get('complexidade_score')}) |",
            f"| {'Domain' if en else 'Domínio'} | {b.get('dominio')} |",
            f"| {'Tables' if en else 'Tabelas'} | {', '.join(f'`{t}`' for t in b.get('tabelas') or []) or '—'} |",
            f"| {'Writes' if en else 'Escrita'} | {', '.join(f'`{t}`' for t in b.get('tabelas_escrita') or []) or '—'} |",
            f"| CTEs | {', '.join(b.get('ctes') or []) or '—'} |",
            f"| PII | {('yes' if (b.get('pii') or {}).get('exposto') else 'no') if en else ('sim' if (b.get('pii') or {}).get('exposto') else 'não')} |",
            "",
            "```sql",
            b.get("sql") or "",
            "```",
            "",
        ])

    out_file.write_text("\n".join(lines), encoding="utf-8")
    return out_file


def exportar_briefing(catalog: Dict[str, Any], output_dir: Path, filename: str = "BRIEFING.md") -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / filename
    brief = catalog.get("briefing") or {}
    stats = catalog.get("stats") or {}
    en = str((catalog.get("meta") or {}).get("locale") or "pt").lower().startswith("en")
    lines = [
        f"# {brief.get('headline', 'Briefing Acervo')}",
        "",
        brief.get("risco_imediato", ""),
        "",
        "## Who this is for" if en else "## Para quem isto existe",
        "",
        *[f"- {item}" for item in brief.get("para_quem", [])],
        "",
        "## The pain" if en else "## A dor",
        "",
        *[f"- {item}" for item in brief.get("dores", [])],
        "",
        "## Findings from this run" if en else "## Achados desta geração",
        "",
        *[f"- {item}" for item in brief.get("achados", [])],
        "",
        f"{'Health' if en else 'Saúde'}: **{stats.get('saude', 0)}** · {'Twins' if en else 'Gêmeos'}: **{stats.get('gemeos', 0)}** · Hubs: **{stats.get('hubs', 0)}** · PII: **{stats.get('pii', 0)}**",
        "",
        "## Next steps" if en else "## Próximos passos",
        "",
        *[f"- {item}" for item in brief.get("proximos", [])],
        "",
    ]
    out_file.write_text("\n".join(lines), encoding="utf-8")
    return out_file


def exportar_pr_comment(catalog: Dict[str, Any], output_dir: Path, filename: str = "PR_COMMENT.md") -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / filename
    try:
        body = schema_impact_markdown(catalog)
    except Exception:
        body = "# Acervo\n\nFalha ao montar o comentário de impacto.\n"
    out_file.write_text(body, encoding="utf-8")
    return out_file
