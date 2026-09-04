#!/usr/bin/env python3
"""CLI do Acervo — inventário estrutural de SQL legado (não executa nada)."""

from __future__ import annotations

import argparse
import sys
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
for path in (PARENT, ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

try:
    from src.core.analyzer import analyze_sql
    from src.core.ai_enricher import maybe_enrich
    from src.core.catalog import build_catalog
    from src.core.collector import collect_sql_files, read_sql_file
    from src.core.generator import normalize_block
    from src.core.interpreter import interpretar
    from src.core.lineage import build_lineage
    from src.core.cascade import ask_catalog, cascade_from_table
    from src.core.i18n import normalize_locale
    from src.core.translator import pretty_sql, transpile_sql
    from src.exporters.html_exporter import render_page
    from src.exporters.json_exporter import exportar_catalogo_json
    from src.exporters.markdown_exporter import exportar_briefing, exportar_markdown, exportar_pr_comment
    from src.exporters.sql_exporter import exportar_queries_sql
except ImportError:
    from core.analyzer import analyze_sql
    from core.ai_enricher import maybe_enrich
    from core.catalog import build_catalog
    from core.collector import collect_sql_files, read_sql_file
    from core.generator import normalize_block
    from core.interpreter import interpretar
    from core.lineage import build_lineage
    from core.cascade import ask_catalog, cascade_from_table
    from core.i18n import normalize_locale
    from core.translator import pretty_sql, transpile_sql
    from exporters.html_exporter import render_page
    from exporters.json_exporter import exportar_catalogo_json
    from exporters.markdown_exporter import exportar_briefing, exportar_markdown, exportar_pr_comment
    from exporters.sql_exporter import exportar_queries_sql


RESET = "\033[0m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
DIM = "\033[2m"
BOLD = "\033[1m"


def _c(code: str, text: str) -> str:
    if not sys.stdout.isatty():
        return text
    return f"{code}{text}{RESET}"


def _print(code: str, text: str) -> None:
    print(_c(code, text))


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="acervo",
        description="Acervo — inventário estrutural de SQL legado (não executa nada).",
    )
    parser.add_argument(
        "queries",
        nargs="?",
        default=None,
        help="Pasta com arquivos .sql (leitura recursiva). Alternativa: --input.",
    )
    parser.add_argument("-i", "--input", dest="input_dir", default=None, help="Pasta de entrada (alias de queries)")
    parser.add_argument("-o", "--output", default="output", help="Pasta de saída (padrão: output)")
    parser.add_argument("-t", "--title", default="Observatório de Queries SQL", help="Título do catálogo")
    parser.add_argument(
        "-d",
        "--dialect",
        default=None,
        help="Dialeto de origem (postgres, mysql, tsql, snowflake, bigquery, oracle...). Auto se omitido.",
    )
    parser.add_argument(
        "--target-dialect",
        default=None,
        help="Transpila cada query para este dialeto (ansi, snowflake, bigquery, mysql, tsql...)",
    )
    parser.add_argument("--serve", action="store_true", help="Sobe um servidor local e abre o HTML")
    parser.add_argument("--port", type=int, default=8765, help="Porta do --serve (padrão: 8765)")
    parser.add_argument("--open", action="store_true", help="Abre o HTML no navegador após gerar")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Falha (exit 2) se houver insight crítico, parse falho ou (com --require-docs) cabeçalho ausente",
    )
    parser.add_argument("--require-docs", action="store_true", help="Com --check, também falha se faltar -- Resumo:")
    parser.add_argument("--ai", action="store_true", help="Enriquece descrições via LLM (ACERVO_LLM_URL / OPENAI_API_KEY)")
    parser.add_argument("--pr-comment", action="store_true", help="Gera output/PR_COMMENT.md para colar no PR")
    parser.add_argument("--baseline", default=None, help="catalogo.json anterior — ativa o delta de PR (SQLPrism-style)")
    parser.add_argument("--table", default=None, help="Imprime o blast radius + cascata desta tabela")
    parser.add_argument("--ask", default=None, help="Pergunta estrutural: table:cidadao col:cns tag:CTE tipo:UPDATE")
    parser.add_argument(
        "--locale",
        default="pt",
        choices=["pt", "en", "pt-BR", "en-US"],
        help="Idioma do catálogo (pt ou en). O SQL não é traduzido.",
    )
    parser.add_argument(
        "--redact-pii",
        action="store_true",
        help="Mascara literais de PII no SQL exportado (catálogo compartilhável)",
    )
    return parser.parse_args(argv)


def process_files(
    files: List[Path],
    queries_dir: Path,
    dialect: Optional[str],
    target_dialect: Optional[str],
    use_ai: bool,
    locale: str = "pt",
) -> tuple[List[Dict], Dict]:
    blocks: List[Dict] = []
    processed = skipped = failed = 0

    for file in files:
        try:
            relative = file.relative_to(queries_dir).as_posix()
        except ValueError:
            relative = file.name
        _print(DIM, f"  · {relative}")
        try:
            sql, meta = read_sql_file(file)
            if not sql:
                _print(YELLOW, f"    vazia — ignorada{(' (' + meta.get('detalhe', '') + ')') if meta.get('detalhe') else ''}")
                skipped += 1
                continue

            analysis = analyze_sql(sql, dialect=dialect)
            if not analysis or "erro" in analysis:
                _print(YELLOW, f"    parse falhou — {analysis.get('detalhe', 'desconhecido')}")
                skipped += 1
                failed += 1
                continue

            info = interpretar(analysis, arquivo=relative, sql=sql, locale=locale)
            info["sql_pretty"] = pretty_sql(sql, info.get("dialect"))
            if target_dialect:
                translated = transpile_sql(sql, source=info.get("dialect"), target=target_dialect)
                info["sql_targets"] = translated
                if translated.get(target_dialect):
                    info["sql_pretty"] = translated[target_dialect]
            block = normalize_block(info, relative, sql, len(blocks) + 1)
            block = maybe_enrich(block, use_ai)
            blocks.append(block)
            processed += 1
            if analysis.get("parse_mode") == "heuristic":
                _print(YELLOW, "    aviso: extração heurística (AST indisponível)")
        except Exception as exc:
            _print(RED, f"    erro: {exc}")
            failed += 1

    run = {
        "processed": processed,
        "skipped": skipped,
        "failed": failed,
        "dialect": dialect or "auto",
        "target_dialect": target_dialect,
        "files": len(files),
        "ai": use_ai,
        "baseline": None,
        "locale": locale,
        "redact_pii": False,
    }
    return blocks, run


def serve_output(output_dir: Path, port: int) -> None:
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(output_dir), **kwargs)

        def log_message(self, fmt: str, *args) -> None:
            _print(DIM, "  " + (fmt % args))

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}/consultas.html"
    _print(GREEN, f"\n  Servindo {url}")
    _print(DIM, "  Ctrl+C para encerrar.\n")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        _print(CYAN, "\n  Encerrado.")


def _check_should_fail(catalog: Dict, run: Dict, require_docs: bool) -> Optional[str]:
    stats = catalog.get("stats") or {}
    reasons = []
    if stats.get("criticos", 0):
        reasons.append(f"{stats['criticos']} insight(s) crítico(s)")
    if run.get("failed", 0):
        reasons.append(f"{run['failed']} arquivo(s) com falha de parse")
    if require_docs and stats.get("sem_header", 0):
        reasons.append(f"{stats['sem_header']} arquivo(s) sem cabeçalho")
    if not reasons:
        return None
    return "; ".join(reasons)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    raw_input = args.input_dir or args.queries or "queries"
    if raw_input in {"catalog", "build"} and not args.input_dir:
        raw_input = "queries"
    queries_dir = Path(raw_input).resolve()
    output_dir = Path(args.output).resolve()

    if not queries_dir.exists() or not queries_dir.is_dir():
        _print(RED, f"Diretório inválido: {queries_dir}")
        return 1

    print()
    _print(BOLD, "  Acervo")
    _print(DIM, "  ·  inventário de SQL legado")
    _print(DIM, f"  lendo  {queries_dir}")
    print()

    locale = normalize_locale(args.locale)
    files = collect_sql_files(queries_dir)
    _print(CYAN, f"  {len(files)} arquivo(s) .sql")
    _print(DIM, f"  locale {locale}{' · PII mascarado' if args.redact_pii else ''}")

    blocks, run = process_files(files, queries_dir, args.dialect, args.target_dialect, args.ai, locale=locale)
    run["redact_pii"] = bool(args.redact_pii)

    print()
    _print(BOLD, "  Resumo")
    print(f"    processadas  {run['processed']}")
    print(f"    ignoradas    {run['skipped']}")
    print(f"    com erro     {run['failed']}")

    if not blocks:
        _print(RED, "\n  Nenhuma query válida. HTML não gerado.")
        return 1

    lineage = build_lineage(blocks)
    if args.baseline:
        run["baseline"] = Path(args.baseline).resolve()
    catalog = build_catalog(blocks, args.title, lineage, run)

    output_dir.mkdir(parents=True, exist_ok=True)
    sql_file = exportar_queries_sql(catalog, output_dir)
    json_file = exportar_catalogo_json(catalog, output_dir)
    md_file = exportar_markdown(catalog, output_dir)
    brief_file = exportar_briefing(catalog, output_dir)
    pr_file = None
    if args.pr_comment or args.check:
        pr_file = exportar_pr_comment(catalog, output_dir)

    html = render_page(catalog)
    out_file = output_dir / "consultas.html"
    out_file.write_text(html, encoding="utf-8")

    print()
    _print(GREEN, "  Artefatos")
    print(f"    {out_file}")
    print(f"    {sql_file}")
    print(f"    {json_file}")
    print(f"    {md_file}")
    print(f"    {brief_file}")
    if pr_file:
        print(f"    {pr_file}")
    print()
    stats = catalog.get("stats") or {}
    print(f"    saúde {stats.get('saude')} · PII {stats.get('pii')} · gêmeos {stats.get('gemeos')} · hubs {stats.get('hubs')} · implícitas {stats.get('implied')}")
    print()

    if args.table:
        row = next((r for r in (catalog.get("impact") or []) if (r.get("tabela") or "").lower() == args.table.lower()), None)
        casc = cascade_from_table(args.table, blocks)
        _print(BOLD, f"  Impacto · {args.table}")
        if row:
            print(f"    raio {row.get('raio')} · risco {row.get('risco')} · mutações {row.get('mutacoes')}")
            print(f"    consultas: {', '.join(row.get('titulos') or [])}")
        print(f"    cascata alcance {casc.get('alcance')}")
        for hop in casc.get("hops") or []:
            print(f"    hop {hop.get('hop')} · {hop.get('rotulo')}")
            for q in hop.get("queries") or []:
                print(f"      - {q.get('arquivo')} · {q.get('titulo')}")
            for t in hop.get("tabelas") or []:
                print(f"      - tabela {t}")
        print()

    if args.ask:
        hits = ask_catalog(catalog, args.ask)
        _print(BOLD, f"  Ask · {args.ask} · {len(hits)} resultado(s)")
        for q in hits[:30]:
            print(f"    {q.get('id')}  {q.get('arquivo')}  {q.get('titulo')}")
        print()

    if args.check:
        reason = _check_should_fail(catalog, run, args.require_docs)
        if reason:
            _print(RED, f"  --check: {reason}. CI deve falhar.")
            return 2

    if args.serve:
        serve_output(output_dir, args.port)
        return 0

    if args.open:
        webbrowser.open(out_file.as_uri())

    return 0


if __name__ == "__main__":
    sys.exit(main())
