from pathlib import Path

from src.core.cascade import ask_catalog, cascade_from_table, diff_against_baseline
from src.core.implied import build_implied_keys
from src.core.smells import extra_smells


def test_not_in_and_insert_smells():
    smells = extra_smells(
        {"tipo": "SELECT", "ctes": [], "joins_count": 0, "distinct": False},
        "SELECT 1 WHERE id NOT IN (SELECT id FROM t)",
    )
    assert any(s["codigo"] == "not-in-subquery" for s in smells)
    insert = extra_smells({"tipo": "INSERT", "ctes": [], "joins_count": 0}, "INSERT INTO dest SELECT * FROM src")
    assert any(s["codigo"] == "insert-no-columns" for s in insert)


def test_unused_cte():
    sql = "WITH morta AS (SELECT 1 AS x) SELECT 2"
    smells = extra_smells({"tipo": "SELECT", "ctes": ["morta"], "joins_count": 0}, sql)
    assert any(s["codigo"] == "unused-cte" for s in smells)


def test_implied_keys_from_shared_column():
    blocks = [
        {"id": "q-001", "tabelas": ["tb_fat_cidadao_pec", "tb_fat_cidadao_territorio"], "colunas": ["co_fat_cidadao_pec"], "uso_colunas": {"join": ["pec.co_fat_cidadao_pec"]}},
        {"id": "q-002", "tabelas": ["tb_fat_proced_atend_proced"], "colunas": ["co_fat_cidadao_pec"], "uso_colunas": {}},
    ]
    keys = build_implied_keys(blocks)
    assert keys
    assert keys[0]["coluna"] == "co_fat_cidadao_pec"
    assert keys[0]["juntas"] >= 2


def test_cascade_readers_then_writers():
    blocks = [
        {"id": "q-001", "titulo": "upd", "arquivo": "a.sql", "tipo": "UPDATE", "tabelas": ["tb_x"], "tabelas_escrita": ["tb_x"], "tabelas_leitura": []},
        {"id": "q-002", "titulo": "etl", "arquivo": "b.sql", "tipo": "INSERT", "tabelas": ["tb_x", "tb_y"], "tabelas_escrita": ["tb_y"], "tabelas_leitura": ["tb_x"]},
        {"id": "q-003", "titulo": "dash", "arquivo": "c.sql", "tipo": "SELECT", "tabelas": ["tb_y"], "tabelas_escrita": [], "tabelas_leitura": ["tb_y"]},
    ]
    casc = cascade_from_table("tb_x", blocks)
    assert casc["alcance"] >= 1
    hops = {h["hop"]: h for h in casc["hops"]}
    assert 1 in hops
    assert any(q["id"] == "q-002" for q in hops[1]["queries"])
    assert 3 in hops
    assert any(q["id"] == "q-003" for q in hops[3]["queries"])


def test_delta_detects_hash_change(tmp_path: Path):
    baseline = {
        "queries": [
            {"id": "q-001", "arquivo": "a.sql", "hash": "old", "titulo": "A", "tipo": "SELECT"},
            {"id": "q-002", "arquivo": "b.sql", "hash": "same", "titulo": "B", "tipo": "SELECT"},
            {"id": "q-004", "arquivo": "d.sql", "hash": "d", "titulo": "D", "tipo": "SELECT"},
        ]
    }
    path = tmp_path / "catalogo.json"
    path.write_text(__import__("json").dumps(baseline), encoding="utf-8")
    blocks = [
        {"id": "q-001", "arquivo": "a.sql", "hash": "new", "titulo": "A", "tipo": "SELECT", "tabelas": ["tb_x"]},
        {"id": "q-002", "arquivo": "b.sql", "hash": "same", "titulo": "B", "tipo": "SELECT", "tabelas": ["tb_z"]},
        {"id": "q-003", "arquivo": "c.sql", "hash": "c", "titulo": "C", "tipo": "SELECT", "tabelas": ["tb_x"]},
        {"id": "q-004", "arquivo": "d.sql", "hash": "d", "titulo": "D", "tipo": "SELECT", "tabelas": ["tb_x"]},
    ]
    delta = diff_against_baseline(blocks, path)
    assert delta["changed"][0]["arquivo"] == "a.sql"
    assert any(r["arquivo"] == "c.sql" for r in delta["added"])
    assert "tb_x" in delta["tables_touched"]
    assert any(r["arquivo"] == "d.sql" for r in delta["impacted"])


def test_ask_table_filter():
    catalog = {
        "queries": [
            {"id": "q-001", "titulo": "PA", "arquivo": "h.sql", "tipo": "SELECT", "tabelas": ["tb_dim_tempo"], "colunas": ["nu_ano"], "tags": ["Hipertensão"], "sql": "select", "descricao": "", "uso_colunas": {}},
            {"id": "q-002", "titulo": "Vacina", "arquivo": "v.sql", "tipo": "UPDATE", "tabelas": ["tb_fat_vacina"], "colunas": [], "tags": [], "sql": "update", "descricao": "", "uso_colunas": {}},
        ]
    }
    hits = ask_catalog(catalog, "table:tempo tipo:select")
    assert len(hits) == 1
    assert hits[0]["id"] == "q-001"
