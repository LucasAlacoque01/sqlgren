from src.core.catalog import build_catalog
from src.core.i18n import msg, normalize_locale, pitch
from src.core.interpreter import gerar_insights, interpretar
from src.core.redact import redact_catalog, redact_sql


def test_locale_normalizes():
    assert normalize_locale("en-US") == "en"
    assert normalize_locale("pt-BR") == "pt"
    assert normalize_locale(None) == "pt"


def test_english_insights_and_pitch():
    assert "header" in msg("missing-header", "en").lower()
    assert "warehouse" in pitch("en").lower()
    info = {
        "tipo": "UPDATE",
        "filtros": [],
        "tabelas": ["tb_x"],
        "pii": {},
        "complexidade": "Baixa",
        "joins_count": 0,
        "subqueries": 0,
        "parse_mode": "ast",
    }
    insights = gerar_insights(info, "UPDATE tb_x SET a = 1", locale="en")
    assert any(i["codigo"] == "unfiltered-mutation" for i in insights)
    assert any("WHERE" in i["mensagem"] for i in insights)


def test_english_description():
    block = interpretar(
        {
            "tipo": "SELECT",
            "tipo_semantico": "Listagem",
            "tabelas": ["people"],
            "metricas": ["COUNT"],
            "dimensoes": ["year"],
            "ctes": [],
            "joins_count": 0,
            "pii": {},
            "complexidade": "Baixa",
            "comentario": "",
        },
        arquivo="people.sql",
        sql="SELECT COUNT(*) FROM people GROUP BY year",
        locale="en",
    )
    assert "computing" in block["descricao"] or "COUNT" in block["descricao"]
    assert block["locale"] == "en"


def test_redact_masks_email_and_cpf():
    sql = "SELECT * FROM t WHERE email = 'a@b.com' AND cpf = '123.456.789-09' AND senha = 'segredo'"
    out = redact_sql(sql)
    assert "a@b.com" not in out
    assert "123.456.789-09" not in out
    assert "segredo" not in out
    assert "[REDACTED_EMAIL]" in out
    assert "[REDACTED]" in out


def test_redact_catalog_keeps_pii_signal():
    catalog = {
        "meta": {"title": "X"},
        "queries": [{
            "sql": "SELECT nu_cns FROM t WHERE email = 'a@b.com'",
            "sql_pretty": "SELECT nu_cns FROM t WHERE email = 'a@b.com'",
            "pii": {"exposto": True, "hits": [{"codigo": "cns", "coluna": "nu_cns", "rotulo": "CNS"}]},
        }],
    }
    out = redact_catalog(catalog)
    assert out["meta"]["redacted"] is True
    assert "a@b.com" not in out["queries"][0]["sql"]
    assert out["queries"][0]["pii"]["exposto"] is True


def test_catalog_meta_locale_and_redact():
    blocks = [{
        "id": "q-001",
        "arquivo": "a.sql",
        "titulo": "A",
        "descricao": "Listagem",
        "tipo": "SELECT",
        "tipo_semantico": "Listagem",
        "complexidade": "Baixa",
        "tabelas": ["tb_x"],
        "tabelas_leitura": ["tb_x"],
        "tabelas_escrita": [],
        "colunas": ["email"],
        "metricas": [],
        "dimensoes": [],
        "ctes": [],
        "joins": [],
        "joins_count": 0,
        "insights": [],
        "dominio": "Geral",
        "tags": [],
        "sql": "SELECT email FROM tb_x WHERE email = 'a@b.com'",
        "sql_pretty": "SELECT email FROM tb_x WHERE email = 'a@b.com'",
        "uso_colunas": {"select": ["email"], "where": ["email"], "join": [], "group": [], "order": [], "having": []},
        "column_lineage": [],
        "pii": {"hits": [{"codigo": "email", "coluna": "email", "rotulo": "E-mail"}], "literais": ["email-literal"], "exposto": True, "quantidade": 2},
        "tem_header": True,
        "parse_mode": "ast",
        "linhas": 1,
        "hash": "abc",
    }]
    catalog = build_catalog(blocks, "Acervo", {"tables": [], "nodes": [], "edges": []}, {"locale": "en", "redact_pii": True, "dialect": "auto"})
    assert catalog["meta"]["locale"] == "en"
    assert catalog["meta"]["redacted"] is True
    assert "a@b.com" not in catalog["queries"][0]["sql"]
    assert "warehouse" in catalog["meta"]["pitch"].lower()
    assert "this week" in catalog["briefing"]["headline"].lower()
