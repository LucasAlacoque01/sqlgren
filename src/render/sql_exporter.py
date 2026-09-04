from pathlib import Path
from typing import List, Dict


def exportar_queries_sql(
    blocks: List[Dict],
    output_dir: Path,
    filename: str = "queries_organizadas.sql"
) -> Path:
    """
    Gera um único arquivo .sql contendo todas as queries
    organizadas e documentadas.
    """

    output_dir.mkdir(exist_ok=True)
    out_file = output_dir / filename

    with out_file.open("w", encoding="utf-8") as f:
        f.write("-- QUERIES SQL ORGANIZADAS\n")
        f.write("-- Gerado automaticamente pelo SQL DocGen\n\n")

        # Índice
        for i, b in enumerate(blocks, 1):
            f.write(
                f"-- {i}. {b.get('titulo')} "
                f"[{b.get('complexidade')}]\n"
            )

        f.write("\n")

        # Conteúdo completo
        for i, b in enumerate(blocks, 1):
            f.write(f"""
-- {i}. {b.get('titulo')}
-- {b.get('descricao')}
-- Tipo: {b.get('tipo')}
-- Complexidade: {b.get('complexidade')}
-- Tabelas: {", ".join(b.get("tabelas", [])) or "—"}
-- Arquivo: {b.get("arquivo")}
{b.get("sql")}

""")

    return out_file
