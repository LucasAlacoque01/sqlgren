from src.cli import _check_should_fail, parse_args


def test_parse_input_and_target_dialect():
    args = parse_args(["queries", "--title", "Acervo Enterprise", "--target-dialect", "snowflake", "--check"])
    assert args.queries == "queries"
    assert args.target_dialect == "snowflake"
    assert args.check is True


def test_parse_input_flag():
    args = parse_args(["--input", "queries", "-o", "output", "--pr-comment"])
    assert args.input_dir == "queries"
    assert args.pr_comment is True


def test_parse_ask_table_baseline():
    args = parse_args(["queries", "--ask", "table:cidadao", "--table", "tb_dim_tempo", "--baseline", "output/catalogo.json"])
    assert args.ask == "table:cidadao"
    assert args.table == "tb_dim_tempo"
    assert args.baseline == "output/catalogo.json"


def test_parse_locale_and_redact():
    args = parse_args(["queries", "--locale", "en", "--redact-pii"])
    assert args.locale == "en"
    assert args.redact_pii is True


def test_check_fails_on_criticos():
    reason = _check_should_fail({"stats": {"criticos": 1, "sem_header": 0}}, {"failed": 0}, False)
    assert reason
    assert "crítico" in reason


def test_check_fails_on_parse_and_docs():
    reason = _check_should_fail({"stats": {"criticos": 0, "sem_header": 2}}, {"failed": 1}, True)
    assert "parse" in reason
    assert "cabeçalho" in reason


def test_check_passes_clean():
    assert _check_should_fail({"stats": {"criticos": 0, "sem_header": 0}}, {"failed": 0}, False) is None
