from src.core.intelligence import build_impact, compute_health, find_twins
from src.core.interpreter import gerar_insights, interpretar


def test_twins_detect_overlap():
    blocks = [
        {
            "id": "q-001",
            "titulo": "A",
            "arquivo": "a.sql",
            "dominio": "Hipertensão",
            "tabelas": ["tb_fat_proced_atend_proced", "tb_dim_tempo"],
            "metricas": ["COUNT"],
            "sql": "SELECT COUNT(*) FROM tb_fat_proced_atend_proced JOIN tb_dim_tempo ON 1=1",
        },
        {
            "id": "q-002",
            "titulo": "B",
            "arquivo": "b.sql",
            "dominio": "Hipertensão",
            "tabelas": ["tb_fat_proced_atend_proced", "tb_dim_tempo"],
            "metricas": ["COUNT"],
            "sql": "SELECT COUNT(DISTINCT x) FROM tb_fat_proced_atend_proced JOIN tb_dim_tempo ON 1=1",
        },
    ]
    twins = find_twins(blocks, threshold=0.3)
    assert twins
    assert twins[0]["a"] == "q-001"
    assert twins[0]["score"] >= 50


def test_twins_classify_gemeo_vs_parecido():
    same = {
        "tabelas": ["t1", "t2"],
        "metricas": ["COUNT"],
        "dominio": "X",
        "sql": "select count(*) from t1 join t2 on t1.id = t2.id where ano = 2024",
    }
    a = {"id": "q-001", "titulo": "A", "arquivo": "a.sql", **same}
    b = {"id": "q-002", "titulo": "B", "arquivo": "b.sql", **same}
    twins = find_twins([a, b], threshold=0.42)
    assert twins
    assert twins[0]["kind"] == "gemeo"


def test_impact_marks_mutation_as_high():
    blocks = [
        {"id": "q-001", "titulo": "upd", "tipo": "UPDATE", "tabelas": ["tb_x"], "tabelas_escrita": ["tb_x"], "tabelas_leitura": []},
        {"id": "q-002", "titulo": "sel", "tipo": "SELECT", "tabelas": ["tb_x"], "tabelas_escrita": [], "tabelas_leitura": ["tb_x"]},
    ]
    tables = [{"nome": "tb_x", "uso": 2, "queries": ["q-001", "q-002"]}]
    impact = build_impact(blocks, tables)
    assert impact[0]["risco"] == "alto"
    assert impact[0]["raio"] == 2
    assert impact[0]["impactados"]
    assert impact[0]["impactados"][0]["id"] == "q-002"


def test_unfiltered_mutation_is_critical():
    info = {
        "tipo": "DELETE",
        "tabelas": ["tb_x"],
        "filtros": [],
        "joins_count": 0,
        "comentario": "limpa tabela",
    }
    found = gerar_insights(info, "DELETE FROM tb_x")
    assert any(i["codigo"] == "unfiltered-mutation" and i["nivel"] == "critico" for i in found)


def test_interpretar_adds_domain_and_pii_tag():
    info = {
        "tipo": "SELECT",
        "tipo_semantico": "Listagem",
        "tabelas": ["tb_fat_cidadao_pec"],
        "colunas": ["nu_cns"],
        "comentario": "Cidadãos ativos no território",
        "complexidade": "Baixa",
        "pii": {"exposto": True, "hits": [{"codigo": "cns", "coluna": "nu_cns", "rotulo": "CNS"}], "literais": [], "quantidade": 1},
        "ctes": [],
        "metricas": [],
        "joins_count": 0,
    }
    out = interpretar(info, arquivo="cadastro/cidadaos.sql", sql="-- Resumo: Cidadãos\nSELECT nu_cns FROM tb_fat_cidadao_pec")
    assert out["dominio"] == "Cadastro"
    assert "PII" in out["tags"]
    assert any(i["codigo"] == "pii-exposure" for i in out["insights"])


def test_health_penalizes_pii_and_criticos():
    clean = compute_health(
        [{"tem_header": True, "pii": {"exposto": False}, "parse_mode": "ast"}],
        {"failed": 0},
        criticos=0,
        alerts=0,
        coverage=100,
    )
    dirty = compute_health(
        [{"tem_header": False, "pii": {"exposto": True}, "parse_mode": "heuristic"}],
        {"failed": 1},
        criticos=2,
        alerts=5,
        coverage=50,
    )
    assert clean > dirty
    assert 0 <= dirty <= 100
    assert clean <= 100
