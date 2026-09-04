from pathlib import Path

from src.core.catalog import build_catalog
from src.core.generator import normalize_block
from src.core.lineage import build_lineage
from src.exporters.html_exporter import render_page
from src.exporters.json_exporter import exportar_catalogo_json
from src.exporters.markdown_exporter import exportar_briefing, exportar_markdown, exportar_pr_comment
from src.exporters.sql_exporter import exportar_queries_sql


def _sample_catalog():
    raw = {
        "titulo": "Cidadãos ativos",
        "descricao": "Listagem em SELECT sobre tb_fat_cidadao_pec.",
        "tipo": "SELECT",
        "tipo_semantico": "Listagem",
        "complexidade": "Baixa",
        "complexidade_score": 1.0,
        "tabelas": ["tb_fat_cidadao_pec"],
        "tabelas_leitura": ["tb_fat_cidadao_pec"],
        "tabelas_escrita": [],
        "colunas": ["nu_cns"],
        "metricas": [],
        "dimensoes": [],
        "ctes": [],
        "joins": [],
        "joins_count": 0,
        "insights": [{"nivel": "ok", "codigo": "clean", "mensagem": "ok"}],
        "dominio": "Cadastro",
        "tags": ["Cadastro", "SELECT"],
        "dialect": "postgres",
        "sql_pretty": "SELECT nu_cns FROM tb_fat_cidadao_pec",
        "uso_colunas": {"select": ["nu_cns"], "where": [], "join": [], "group": [], "order": [], "having": []},
        "column_lineage": [{"coluna": "nu_cns", "origens": ["tb_fat_cidadao_pec.nu_cns"]}],
        "pii": {"hits": [{"codigo": "cns", "coluna": "nu_cns", "rotulo": "CNS"}], "literais": [], "exposto": True, "quantidade": 1},
        "comentario": "Cidadãos ativos",
        "tem_header": True,
        "parse_mode": "ast",
        "linhas": 2,
        "hash": "abc123",
    }
    block = normalize_block(raw, "cadastro/cidadaos.sql", "SELECT nu_cns FROM tb_fat_cidadao_pec", 1)
    lineage = build_lineage([block])
    return build_catalog([block], "Acervo Teste", lineage, {"processed": 1, "skipped": 0, "failed": 0, "dialect": "postgres", "files": 1})


def test_exporters_write_artifacts(tmp_path: Path):
    catalog = _sample_catalog()
    json_file = exportar_catalogo_json(catalog, tmp_path)
    md_file = exportar_markdown(catalog, tmp_path)
    brief = exportar_briefing(catalog, tmp_path)
    sql_file = exportar_queries_sql(catalog, tmp_path)
    pr = exportar_pr_comment(catalog, tmp_path)
    html = render_page(catalog)

    assert json_file.exists() and json_file.stat().st_size > 20
    assert "Cidadãos ativos" in md_file.read_text(encoding="utf-8")
    assert "Briefing" in brief.read_text(encoding="utf-8") or "Inventário" in brief.read_text(encoding="utf-8")
    assert "SELECT nu_cns" in sql_file.read_text(encoding="utf-8")
    assert "hubs" in pr.read_text(encoding="utf-8").lower() or "Hubs" in pr.read_text(encoding="utf-8")
    assert "<!doctype html>" in html.lower()
    assert "sqldoc-data" in html
    assert "Acervo Teste" in html


def test_catalog_includes_graph_and_pii_stats():
    catalog = _sample_catalog()
    assert catalog["stats"]["pii"] == 1
    assert "graph" in catalog
    assert catalog["queries"][0]["column_lineage"]
