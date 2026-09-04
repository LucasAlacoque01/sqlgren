import sys
from pathlib import Path
from typing import List, Dict
from script.analyzer import analyze_sql
from script.interpreter import interpretar
from render.html_theme import render_page
from render.sql_exporter import exportar_queries_sql


def main():
    # Validação de argumentos
    if len(sys.argv) < 2:
        print(" Uso incorreto.")
        print(" Exemplo: python cli.py ./queries")
        sys.exit(1)

    queries_dir = Path(sys.argv[1]).resolve()


    if not queries_dir.exists() or not queries_dir.is_dir():
        print(f" Diretório inválido: {queries_dir}")
        sys.exit(1)

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    print(f" Lendo queries de: {queries_dir.resolve()}")

    sql_files = list(queries_dir.rglob("*.sql"))
    print(f" Arquivos encontrados: {len(sql_files)}")

    blocks: List[Dict] = []

    processed = 0
    skipped = 0
    failed = 0

    # Processamento isolado por arquivo
    for file in sql_files:
        relative = file.relative_to(queries_dir)
        print(f" Processando: {relative}")

        try:
            sql = file.read_text(encoding="utf-8").strip()
            if not sql:
                print("    Arquivo vazio — ignorado")
                skipped += 1
                continue

            analysis = analyze_sql(sql)

            if not analysis or "erro" in analysis:
                print("    Falha ao analisar SQL — ignorado")
                skipped += 1
                continue

            info = interpretar(analysis)

            blocks.append({
                "arquivo": str(relative),
                "titulo": info.get("titulo"),
                "descricao": info.get("descricao"),
                "complexidade": info.get("complexidade"),
                "tipo": info.get("tipo"),
                "tabelas": info.get("tabelas", []),
                "metricas": info.get("metricas", []),
                "dimensoes": info.get("dimensoes", []),
                "sql": sql,
            })

            processed += 1

        except Exception as e:
            print(f"    Erro inesperado: {e}")
            failed += 1

    #  Resumo final (nível ferramenta real)
    print("\n Resumo da execução")
    print(f"    Processados com sucesso: {processed}")
    print(f"    Ignorados: {skipped}")
    print(f"    Com erro: {failed}")
    
    if not blocks:
        print("\n Nenhuma query válida encontrada. HTML não será gerado.")
        sys.exit(1)

    # Exportação SQL organizada
    sql_file = exportar_queries_sql(blocks, output_dir)
    print(f"\n SQL organizado gerado em: {sql_file.resolve()}")

    #  Geração do HTML
    html = render_page("Documentação de Queries SQL", blocks)
    out_file = output_dir / "consultas.html"
    out_file.write_text(html, encoding="utf-8")

    print(f"\n HTML gerado com sucesso em: {out_file.resolve()}")


if __name__ == "__main__":
    main()