from src.core.analyzer import analyze_sql, heuristic_analyze
from src.core.pii import detect_pii, pii_hits_from_names


HIPERTENSAO = """
-- Resumo: Hipertensos com PA aferida
WITH pacientes_hipertensos AS (
    SELECT DISTINCT FAIP.CO_FAT_CIDADAO_PEC
    FROM TB_FAT_ATD_IND_PROBLEMAS FAIP
    JOIN TB_DIM_CIAP CIAP ON FAIP.CO_DIM_CIAP = CIAP.CO_SEQ_DIM_CIAP
    WHERE CIAP.NU_CIAP IN ('K86', 'K87')
)
SELECT COUNT(DISTINCT pr.co_fat_cidadao_pec) AS total
FROM tb_fat_proced_atend_proced pr
JOIN tb_dim_tempo tdt ON pr.co_dim_tempo = tdt.co_seq_dim_tempo
WHERE pr.co_fat_cidadao_pec IN (SELECT CO_FAT_CIDADAO_PEC FROM pacientes_hipertensos)
"""

CADASTRO = """
-- Resumo: Cidadãos ativos
SELECT pec.no_cidadao, pec.nu_cns, pec.nu_cpf_cidadao
FROM tb_fat_cidadao_pec pec
WHERE pec.st_vivo = 1
LIMIT :limite
"""

UNFILTERED = "UPDATE tb_fat_cidadao_territorio SET st_mudou_se = 1"


def test_analyze_extracts_ctes_and_tables():
    info = analyze_sql(HIPERTENSAO, dialect="postgres")
    assert "erro" not in info
    assert info["tipo"] == "SELECT"
    assert "pacientes_hipertensos" in info["ctes"]
    assert any("tb_fat_proced_atend_proced" in t for t in info["tabelas"])
    assert "COUNT" in info["metricas"]
    assert info["parse_mode"] in {"ast", "heuristic"}


def test_column_lineage_resolves_cte_output():
    sql = """
    WITH pacientes AS (
      SELECT pec.co_fat_cidadao_pec AS id
      FROM tb_fat_cidadao_pec pec
    )
    SELECT id FROM pacientes
    """
    info = analyze_sql(sql, dialect="postgres")
    lineage = info.get("column_lineage") or []
    assert lineage
    names = [row["coluna"].lower() for row in lineage]
    assert "id" in names
    id_row = next(row for row in lineage if row["coluna"].lower() == "id")
    origens = " ".join(id_row.get("origens") or []).lower()
    assert "id" in origens or "cidadao" in origens or "pacientes" in origens


def test_sources_and_sinks():
    sql = """
    INSERT INTO tb_fat_resumo_diario (co_dim_tempo)
    SELECT t.co_seq_dim_tempo FROM tb_dim_tempo t
    """
    info = analyze_sql(sql, dialect="postgres")
    assert info["tipo"] == "INSERT"
    written = [t.lower() for t in info.get("tabelas_escrita") or []]
    assert any("resumo" in t for t in written)
    reads = [t.lower() for t in info.get("tabelas_leitura") or info.get("tabelas") or []]
    assert any("tempo" in t for t in reads)


def test_pii_detects_cns_and_cpf():
    info = analyze_sql(CADASTRO, dialect="postgres")
    pii = info.get("pii") or {}
    assert pii.get("exposto")
    codes = {h["codigo"] for h in pii.get("hits") or []}
    assert "cns" in codes or "cpf" in codes


def test_heuristic_fallback_on_garbage():
    info = heuristic_analyze("SELECT a FROM foo JOIN bar ON a.id = bar.id WHERE a.x = 1")
    assert info["tipo"] == "SELECT"
    assert "foo" in info["tabelas"]
    assert info["parse_mode"] == "heuristic"


def test_pii_hits_from_names():
    result = pii_hits_from_names(["nu_cns", "email"], "SELECT nu_cns FROM t")
    assert result["exposto"]
    assert any(h["codigo"] == "cns" for h in result["hits"])


def test_detect_pii_on_analysis_dict():
    found = detect_pii({"colunas": ["password_hash"], "uso_colunas": {"where": ["token"]}}, "")
    assert found["exposto"]
    assert found["quantidade"] >= 1


def test_empty_sql():
    info = analyze_sql("   ")
    assert "erro" in info
