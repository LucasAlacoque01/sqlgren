"""Normaliza o bloco de uma query para o catálogo."""

from __future__ import annotations

from typing import Any, Dict


def normalize_block(info: Dict[str, Any], arquivo: str, sql: str, index: int) -> Dict[str, Any]:
    if not isinstance(info, dict):
        raise TypeError("info deve ser um dicionário")

    pasta = "raiz"
    if "/" in arquivo:
        pasta = arquivo.rsplit("/", 1)[0]
    elif "\\" in arquivo:
        pasta = arquivo.rsplit("\\", 1)[0]

    return {
        "id": f"q-{index:03d}",
        "index": index,
        "arquivo": arquivo,
        "pasta": pasta,
        "titulo": info.get("titulo") or arquivo,
        "descricao": info.get("descricao") or "",
        "tipo": info.get("tipo") or "UNKNOWN",
        "tipo_semantico": info.get("tipo_semantico") or "Consulta",
        "complexidade": info.get("complexidade") or "Média",
        "complexidade_score": info.get("complexidade_score") or 0,
        "tabelas": info.get("tabelas") or [],
        "tabelas_leitura": info.get("tabelas_leitura") or [],
        "tabelas_escrita": info.get("tabelas_escrita") or [],
        "colunas": info.get("colunas") or [],
        "metricas": info.get("metricas") or [],
        "dimensoes": info.get("dimensoes") or [],
        "ctes": info.get("ctes") or [],
        "ctes_detail": info.get("ctes_detail") or [],
        "joins": info.get("joins") or [],
        "joins_count": info.get("joins_count") or 0,
        "subqueries": info.get("subqueries") or 0,
        "unions": info.get("unions") or 0,
        "window_functions": info.get("window_functions") or [],
        "cases": info.get("cases") or 0,
        "filtros": info.get("filtros") or [],
        "order_by": info.get("order_by") or [],
        "limit": info.get("limit"),
        "distinct": bool(info.get("distinct")),
        "parametros": info.get("parametros") or [],
        "dialect": info.get("dialect") or "auto",
        "dominio": info.get("dominio") or "Geral",
        "tags": info.get("tags") or [],
        "insights": info.get("insights") or [],
        "linhas": info.get("linhas") or (sql.count("\n") + 1 if sql else 0),
        "bytes": info.get("bytes") or len((sql or "").encode("utf-8")),
        "hash": info.get("hash") or "",
        "statements": info.get("statements") or 1,
        "sql": (sql or "").strip(),
        "sql_pretty": info.get("sql_pretty") or (sql or "").strip(),
        "sql_targets": info.get("sql_targets") or {},
        "uso_colunas": info.get("uso_colunas") or {},
        "column_lineage": info.get("column_lineage") or [],
        "join_implicito": bool(info.get("join_implicito")),
        "dono": info.get("dono") or pasta,
        "pii": info.get("pii") or {"hits": [], "literais": [], "exposto": False, "quantidade": 0},
        "parse_mode": info.get("parse_mode") or "ast",
        "parse_warning": info.get("parse_warning"),
        "comentario": info.get("comentario") or "",
        "tem_header": bool(info.get("tem_header")),
        "ai": info.get("ai"),
    }
