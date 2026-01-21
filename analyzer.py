import sqlglot
from sqlglot import exp
from typing import Dict, List, Set, Optional


def analyze_sql(sql: str) -> Optional[Dict]:
    """
    Analisa estruturalmente uma query SQL sem executá-la.

    Retorna informações sobre:
    - tipo da consulta (Listagem ou Agregação)
    - tabelas utilizadas
    - métricas (funções de agregação)
    - dimensões (GROUP BY)
    - quantidade de joins e subqueries
    - nível de complexidade estrutural
    """

    # 1️⃣ Parsing seguro
    try:
        parsed = sqlglot.parse(sql, read="postgres")
        if not parsed:
            raise ValueError("SQL vazio ou inválido")
        ast = parsed[0]
    except Exception as e:
        return {
            "erro": "Falha ao interpretar o SQL",
            "detalhe": str(e),
        }

    # 2️⃣ Coleta estrutural
    tabelas: Set[str] = set()
    metricas: Set[str] = set()
    dimensoes: List[str] = []

    joins = 0
    subqueries = 0

    for node in ast.walk():
        if isinstance(node, exp.Table):
            # Usa sql() para preservar schema se existir
            tabelas.add(node.sql())
        elif isinstance(node, exp.Join):
            joins += 1
        elif isinstance(node, exp.Subquery):
            subqueries += 1
        elif isinstance(node, exp.AggFunc):
            metricas.add(node.sql_name().upper())

    # 3️⃣ GROUP BY (dimensões)
    group = ast.args.get("group")
    if group and group.expressions:
        dimensoes = [expr.sql() for expr in group.expressions]

    # 4️⃣ Tipo da consulta (semântico)
    tipo = "Agregação" if metricas else "Listagem"

    # 5️⃣ Complexidade estrutural (score)
    score = (
        joins * 2
        + subqueries * 3
        + len(metricas) * 1
        + len(dimensoes) * 0.5
    )

    if score <= 3:
        complexidade = "Simples"
    elif score <= 8:
        complexidade = "Média"
    else:
        complexidade = "Pesada"

    # 6️⃣ Retorno rico e extensível
    return {
        "tipo": tipo,
        "tabelas": sorted(tabelas),
        "metricas": sorted(metricas),
        "dimensoes": dimensoes,
        "joins": joins,
        "subqueries": subqueries,
        "complexidade": complexidade,
        "complexidade_score": score,
    }
