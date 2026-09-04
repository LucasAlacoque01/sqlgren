"""SQL concatenado e comentado — artefato de arquivo único."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


def exportar_queries_sql(catalog: Dict[str, Any], output_dir: Path, filename: str = "queries_organizadas.sql") -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / filename
    blocks = catalog.get("queries", [])
    meta = catalog.get("meta", {})

    with out_file.open("w", encoding="utf-8") as f:
        f.write("-- Acervo · queries organizadas\n")
        f.write(f"-- {meta.get('title', 'Catálogo')}\n")
        f.write(f"-- Gerado em {meta.get('generated_at', '')}\n")
        f.write(f"-- Queries: {len(blocks)}\n\n")

        for i, b in enumerate(blocks, 1):
            f.write(f"-- {i}. {b.get('titulo')} [{b.get('complexidade')}] · {b.get('arquivo')}\n")

        f.write("\n")

        for i, b in enumerate(blocks, 1):
            tabelas = ", ".join(b.get("tabelas") or []) or "—"
            f.write(
                f"\n-- ---------------------------------------------------------------------------\n"
                f"-- {i}. {b.get('titulo')}\n"
                f"-- {b.get('descricao')}\n"
                f"-- Tipo: {b.get('tipo')} · {b.get('tipo_semantico')}\n"
                f"-- Complexidade: {b.get('complexidade')} ({b.get('complexidade_score')})\n"
                f"-- Domínio: {b.get('dominio')}\n"
                f"-- Tabelas: {tabelas}\n"
                f"-- Arquivo: {b.get('arquivo')}\n"
                f"-- ---------------------------------------------------------------------------\n"
                f"{b.get('sql')}\n;\n"
            )

    return out_file
