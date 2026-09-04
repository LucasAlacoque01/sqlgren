"""Análise estrutural de SQL via AST (sqlglot) com fallback heurístico e linhagem de colunas."""

from __future__ import annotations

import hashlib
import re
import warnings
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from .pii import detect_pii, pii_hits_from_names

DIALECTS = ("postgres", "tsql", "mysql", "snowflake", "bigquery", "spark", "oracle", "ansi")

STATEMENT_LABELS = {
    "Select": "SELECT",
    "Insert": "INSERT",
    "Update": "UPDATE",
    "Delete": "DELETE",
    "Create": "CREATE",
    "Merge": "MERGE",
    "Drop": "DROP",
    "Command": "COMMAND",
}

_PARAM_RE = re.compile(r"(?<!:):([A-Za-z_][A-Za-z0-9_]*)")
_AT_PARAM_RE = re.compile(r"@([A-Za-z_][A-Za-z0-9_]*)")
_COMMA_JOIN_RE = re.compile(r"\bFROM\s+[\w.]+(\s+\w+)?\s*,\s*[\w.]+", re.I)


def _table_name(node: Any) -> str:
    parts = [p for p in (getattr(node, "catalog", None), getattr(node, "db", None), getattr(node, "name", None)) if p]
    if parts:
        return ".".join(str(p) for p in parts)
    try:
        return node.sql()
    except Exception:
        return str(getattr(node, "name", "") or "")


def _join_kind(node: Any) -> str:
    kind = str(node.args.get("kind") or "").upper()
    side = str(node.args.get("side") or "").upper()
    if side and kind:
        return f"{side} {kind}"
    if side:
        return f"{side} JOIN"
    if kind:
        return f"{kind} JOIN"
    return "JOIN"


def _clause_of(node: Any) -> str:
    try:
        from sqlglot import exp
    except Exception:
        return "select"
    parent = node.parent
    while parent is not None:
        if isinstance(parent, exp.Where):
            return "where"
        if isinstance(parent, exp.Join):
            return "join"
        if isinstance(parent, exp.Group):
            return "group"
        if isinstance(parent, exp.Order):
            return "order"
        if isinstance(parent, exp.Having):
            return "having"
        parent = parent.parent
    return "select"


def _column_usage(ast: Any) -> Dict[str, List[str]]:
    uso: Dict[str, List[str]] = {"select": [], "where": [], "join": [], "group": [], "order": [], "having": []}
    seen: Set[str] = set()
    try:
        from sqlglot import exp
    except Exception:
        return uso
    for col in ast.find_all(exp.Column):
        try:
            name = col.sql()
        except Exception:
            name = str(getattr(col, "name", "") or "")
        clause = _clause_of(col)
        key = f"{clause}:{name.lower()}"
        if key in seen:
            continue
        seen.add(key)
        uso[clause].append(name)
    return {k: v[:80] for k, v in uso.items()}


def _flatten_and(node: Any) -> List[str]:
    if node is None:
        return []
    try:
        from sqlglot import exp
    except Exception:
        return []
    if isinstance(node, exp.And):
        return _flatten_and(node.left) + _flatten_and(node.right)
    try:
        sql = node.sql(pretty=False)
    except Exception:
        sql = str(node)
    return [sql] if sql else []


def _leading_comment(sql: str) -> str:
    lines: List[str] = []
    for raw in sql.splitlines():
        line = raw.strip()
        if not line:
            if lines:
                break
            continue
        if line.startswith("--"):
            lines.append(line[2:].strip())
            continue
        if line.startswith("/*"):
            continue
        break
    text = " ".join(lines).strip()
    text = re.sub(r"^(resumo|título|titulo|desc|descrição|descricao)\s*:\s*", "", text, flags=re.I)
    return text[:240]


def parse_sql(sql: str, preferred: Optional[str] = None) -> Tuple[Optional[str], List[Any], str]:
    """Tenta dialetos em ordem. Retorna (dialeto, trees, modo) onde modo é ast|heuristic."""
    try:
        import sqlglot
        from sqlglot import exp
    except Exception as exc:
        warnings.warn(f"sqlglot indisponível — fallback heurístico ({exc})", RuntimeWarning)
        return None, [], "heuristic"

    order = [preferred] + [d for d in DIALECTS if d != preferred] if preferred else list(DIALECTS)
    last_error: Optional[Exception] = None
    for dialect in order:
        if not dialect:
            continue
        try:
            parsed = sqlglot.parse(sql, read=dialect)
            trees = [t for t in parsed if t is not None]
            if trees:
                return dialect, trees, "ast"
        except Exception as exc:
            last_error = exc
            continue
    if last_error:
        warnings.warn(f"parse AST falhou em todos os dialetos — {last_error}", RuntimeWarning)
    return None, [], "heuristic"


def _alias_table_map(select: Any) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    try:
        from sqlglot import exp
    except Exception:
        return mapping
    sources: List[Any] = []
    frm = select.args.get("from_") if hasattr(select, "args") else None
    if frm is None and hasattr(select, "args"):
        frm = select.args.get("from")
    if frm is not None:
        sources.append(getattr(frm, "this", frm))
    for join in select.args.get("joins") or []:
        sources.append(getattr(join, "this", join))
    for src in sources:
        if src is None:
            continue
        table = src if isinstance(src, exp.Table) else src.find(exp.Table) if hasattr(src, "find") else None
        if table is None:
            continue
        physical = _table_name(table).lower()
        alias = (src.alias_or_name or table.alias_or_name or table.name or "").lower()
        if alias:
            mapping[alias] = physical
        if physical:
            mapping[physical] = physical
    return mapping


def _column_lineage_from_select(select: Any, cte_outputs: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    try:
        from sqlglot import exp
    except Exception:
        return rows
    alias_map = _alias_table_map(select)

    def origins_of(expr: Any) -> List[str]:
        found: List[str] = []
        if expr is None:
            return found
        for col in expr.find_all(exp.Column):
            col_name = col.name or col.sql()
            table_ref = (col.table or "").lower()
            physical = alias_map.get(table_ref, table_ref)
            if physical and physical in cte_outputs:
                for item in cte_outputs[physical]:
                    if str(item.get("coluna", "")).lower() == str(col_name).lower():
                        found.extend(item.get("origens") or [f"{physical}.{col_name}"])
                        break
                else:
                    found.append(f"{physical}.{col_name}")
            elif physical:
                found.append(f"{physical}.{col_name}")
            else:
                found.append(col_name)
        return list(dict.fromkeys(found))

    for expr in select.expressions or []:
        label = expr.alias_or_name or expr.sql()
        if not label:
            continue
        if isinstance(expr, exp.Star) or label == "*":
            rows.append({"coluna": "*", "origens": [f"{t}.*" for t in sorted(set(alias_map.values()))][:12]})
            continue
        inner = expr.this if isinstance(expr, exp.Alias) else expr
        rows.append({"coluna": label, "origens": origins_of(inner)[:24]})
    return rows[:80]


def _cte_lineage(ast: Any) -> Tuple[List[str], List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
    names: List[str] = []
    details: List[Dict[str, Any]] = []
    outputs: Dict[str, List[Dict[str, Any]]] = {}
    try:
        from sqlglot import exp
    except Exception:
        return names, details, outputs
    for cte in ast.find_all(exp.CTE):
        alias = cte.alias
        if not alias:
            continue
        names.append(alias)
        inner = cte.this
        select = inner if isinstance(inner, exp.Select) else (inner.find(exp.Select) if inner is not None else None)
        tabelas: List[str] = []
        colunas: List[str] = []
        cll: List[Dict[str, Any]] = []
        if select is not None:
            for table in select.find_all(exp.Table):
                nome = _table_name(table)
                if nome and nome.lower() not in {n.lower() for n in names}:
                    tabelas.append(nome.lower())
            cll = _column_lineage_from_select(select, outputs)
            colunas = [row["coluna"] for row in cll]
        details.append({
            "nome": alias,
            "tabelas": list(dict.fromkeys(tabelas)),
            "colunas": colunas[:40],
            "column_lineage": cll,
        })
        outputs[alias.lower()] = cll
    return names, details, outputs


def _tables_written(ast: Any) -> List[str]:
    written: List[str] = []
    try:
        from sqlglot import exp
    except Exception:
        return written
    if isinstance(ast, (exp.Insert, exp.Update, exp.Delete, exp.Merge, exp.Create, exp.Drop)):
        target = ast.this
        table = target if isinstance(target, exp.Table) else (target.find(exp.Table) if target is not None and hasattr(target, "find") else None)
        if isinstance(ast, exp.Create) and table is None and target is not None:
            table = target if isinstance(target, exp.Table) else None
        if table is not None:
            written.append(_table_name(table).lower())
        elif target is not None:
            try:
                written.append(str(target.name or target.sql()).lower())
            except Exception:
                pass
    return list(dict.fromkeys(written))


def _sqlglot_lineage(sql: str, dialect: Optional[str], output_cols: Iterable[str]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    try:
        from sqlglot.lineage import lineage
    except Exception:
        return rows
    for col in list(output_cols)[:40]:
        if not col or col == "*":
            continue
        try:
            node = lineage(col, sql, dialect=dialect)
        except Exception:
            continue
        origens: List[str] = []

        def walk(n: Any, depth: int = 0) -> None:
            if n is None or depth > 12:
                return
            children = getattr(n, "downstream", None) or getattr(n, "children", None) or []
            if not children:
                name = getattr(n, "name", None) or str(n)
                source = getattr(n, "source", None)
                if source is not None:
                    try:
                        src_sql = source.sql() if hasattr(source, "sql") else str(source)
                    except Exception:
                        src_sql = str(source)
                    origens.append(f"{src_sql}.{name}" if name else src_sql)
                elif name:
                    origens.append(str(name))
                return
            for child in children:
                walk(child, depth + 1)

        walk(node)
        if origens:
            rows.append({"coluna": col, "origens": list(dict.fromkeys(origens))[:24]})
    return rows


def _analyze_tree(ast: Any) -> Dict[str, Any]:
    try:
        from sqlglot import exp
    except Exception:
        return heuristic_analyze(ast.sql() if hasattr(ast, "sql") else str(ast))

    tabelas: Set[str] = set()
    metricas: Set[str] = set()
    dimensoes: List[str] = []
    colunas: List[str] = []
    joins: List[Dict[str, str]] = []
    window_fns: Set[str] = set()
    parametros: Set[str] = set()
    order_by: List[str] = []

    joins_count = 0
    subqueries = 0
    unions = 0
    cases = 0
    distinct = False
    limit: Optional[str] = None

    ctes, ctes_detail, cte_outputs = _cte_lineage(ast)
    cte_names = {c.lower() for c in ctes}

    for node in ast.walk():
        if isinstance(node, exp.Table):
            name = _table_name(node)
            if name and name.lower() not in cte_names:
                tabelas.add(name.lower())
        elif isinstance(node, exp.Join):
            joins_count += 1
            table = ""
            this = node.this
            if isinstance(this, exp.Table):
                table = _table_name(this)
            elif this is not None:
                table = this.alias_or_name or this.sql()
            joins.append({"tipo": _join_kind(node), "tabela": table})
        elif isinstance(node, exp.Subquery):
            subqueries += 1
        elif isinstance(node, exp.Union):
            unions += 1
        elif isinstance(node, exp.AggFunc):
            metricas.add(node.sql_name().upper())
        elif isinstance(node, exp.Window):
            fn = node.this
            if fn is not None:
                window_fns.add(fn.sql_name().upper() if hasattr(fn, "sql_name") else fn.sql())
        elif isinstance(node, exp.Case):
            cases += 1
        elif isinstance(node, exp.Placeholder):
            parametros.add(node.sql())
        elif isinstance(node, exp.Parameter):
            parametros.add(node.sql())

    try:
        blob = ast.sql()
    except Exception:
        blob = ""
    for match in _PARAM_RE.findall(blob):
        parametros.add(f":{match}")
    for match in _AT_PARAM_RE.findall(blob):
        parametros.add(f"@{match}")

    select = ast if isinstance(ast, exp.Select) else ast.find(exp.Select)
    column_lineage: List[Dict[str, Any]] = []
    if select:
        distinct = bool(select.args.get("distinct"))
        for expr in select.expressions or []:
            label = expr.alias_or_name or expr.sql()
            if label:
                colunas.append(label)
        group = select.args.get("group")
        if group and group.expressions:
            dimensoes = [e.sql() for e in group.expressions]
        order = select.args.get("order")
        if order and order.expressions:
            order_by = [e.sql() for e in order.expressions]
        limit_node = select.args.get("limit")
        if limit_node:
            limit = limit_node.sql()
        column_lineage = _column_lineage_from_select(select, cte_outputs)

    where_node = None
    if isinstance(ast, exp.Select):
        where_node = ast.args.get("where")
    else:
        found = ast.find(exp.Select)
        if found:
            where_node = found.args.get("where")
    if where_node and hasattr(where_node, "this"):
        filtros = _flatten_and(where_node.this)
    else:
        filtros = _flatten_and(where_node)

    statement = "UNKNOWN"
    for cls_name, label in STATEMENT_LABELS.items():
        cls = getattr(exp, cls_name, None)
        if cls is not None and isinstance(ast, cls):
            statement = label
            break
    if statement == "UNKNOWN" and ast.find(exp.Select):
        statement = "SELECT"

    tabelas_escrita = _tables_written(ast)
    tabelas_leitura = sorted(t for t in tabelas if t not in set(tabelas_escrita))

    tipo_semantico = "Agregação" if metricas else "Listagem"
    if statement in {"INSERT", "UPDATE", "DELETE", "MERGE"}:
        tipo_semantico = "Mutação"
    elif statement == "CREATE":
        tipo_semantico = "DDL"
    elif window_fns:
        tipo_semantico = "Analítica"
    elif ctes:
        tipo_semantico = "Pipeline" if metricas else tipo_semantico

    score = (
        joins_count * 2
        + subqueries * 3
        + len(metricas)
        + len(dimensoes) * 0.5
        + len(ctes) * 1.5
        + unions * 2
        + len(window_fns) * 2
        + min(len(filtros), 6) * 0.3
        + cases * 0.4
    )
    if score <= 3:
        complexidade = "Baixa"
    elif score <= 8:
        complexidade = "Média"
    else:
        complexidade = "Alta"

    return {
        "tipo": statement,
        "tipo_semantico": tipo_semantico,
        "tabelas": sorted(tabelas, key=str.lower),
        "tabelas_leitura": tabelas_leitura,
        "tabelas_escrita": tabelas_escrita,
        "colunas": colunas[:80],
        "metricas": sorted(metricas),
        "dimensoes": dimensoes,
        "ctes": ctes,
        "ctes_detail": ctes_detail,
        "joins": joins,
        "joins_count": joins_count,
        "subqueries": subqueries,
        "unions": unions,
        "window_functions": sorted(window_fns),
        "cases": cases,
        "filtros": filtros[:24],
        "order_by": order_by,
        "limit": limit,
        "distinct": distinct,
        "parametros": sorted(parametros),
        "complexidade": complexidade,
        "complexidade_score": round(float(score), 2),
        "uso_colunas": _column_usage(ast),
        "column_lineage": column_lineage,
        "join_implicito": bool(_COMMA_JOIN_RE.search(blob)),
        "parse_mode": "ast",
    }


def heuristic_analyze(sql: str) -> Dict[str, Any]:
    """Parser por regex quando o AST falha — nunca derruba o pipeline."""
    stripped = sql.strip()
    head = re.sub(r"/\*[\s\S]*?\*/", "", stripped)
    head = re.sub(r"^--.*$", "", head, flags=re.M).strip()
    first = (head.split() or ["UNKNOWN"])[0].upper()
    if first == "WITH":
        first = "SELECT"
    tipo = first if first in {"SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "MERGE", "DROP"} else "SELECT"

    ctes = [m.group(1) for m in re.finditer(r"([A-Za-z_][\w]*)\s+AS\s*\(\s*SELECT\b", stripped, re.I)]
    cte_set = {c.lower() for c in ctes}
    skip = {
        "age", "extract", "date", "timestamp", "current_date", "current_timestamp",
        "cast", "coalesce", "nullif", "greatest", "least", "to_char", "to_date", "unnest",
    }
    tables: List[str] = []
    seen: Set[str] = set()
    for match in re.finditer(r"\b(?:FROM|JOIN|UPDATE|INTO|MERGE\s+INTO|DELETE\s+FROM)\s+([A-Za-z_][\w.]*)", stripped, re.I):
        name = match.group(1)
        key = name.lower()
        if key in cte_set or key in skip or key in seen:
            continue
        seen.add(key)
        tables.append(key)

    written: List[str] = []
    for match in re.finditer(r"\b(?:INSERT\s+INTO|UPDATE|DELETE\s+FROM|MERGE\s+INTO|CREATE\s+TABLE)\s+([A-Za-z_][\w.]*)", stripped, re.I):
        written.append(match.group(1).lower())
    written = list(dict.fromkeys(written))

    joins = [
        {"tipo": f"{(m.group(1) or '').strip().upper()} JOIN".strip(), "tabela": m.group(2)}
        for m in re.finditer(r"\b((?:LEFT|RIGHT|FULL|INNER|CROSS)\s+)?JOIN\s+([A-Za-z_][\w.]*)", stripped, re.I)
    ]
    metricas = sorted({m.group(1).upper() for m in re.finditer(r"\b(COUNT|SUM|AVG|MIN|MAX|ROUND)\s*\(", stripped, re.I)})
    group = re.search(r"\bGROUP\s+BY\s+([^;]+?)(?:ORDER|LIMIT|HAVING|$)", stripped, re.I)
    dimensoes = [s.strip() for s in group.group(1).split(",")] if group else []
    colunas: List[str] = []
    select = re.search(r"\bSELECT\b([\s\S]*?)\bFROM\b", stripped, re.I)
    if select:
        for part in select.group(1).split(","):
            alias = re.search(r'\bAS\s+("([^"]+)"|[\w]+)', part, re.I)
            label = (alias.group(2) or alias.group(1)) if alias else part.strip().split()[-1] if part.strip() else ""
            if label and label != "*":
                colunas.append(label.replace('"', "").replace("'", ""))
    where_match = re.search(r"\bWHERE\b([\s\S]*?)(?:GROUP|ORDER|LIMIT|$)", stripped, re.I)
    filtros = [
        s.strip()
        for s in re.split(r"\bAND\b", where_match.group(1) if where_match else "", flags=re.I)
        if s.strip() and len(s.strip()) < 160
    ][:12]

    window_functions = sorted({m.group(1).upper() for m in re.finditer(r"\b(LAG|LEAD|ROW_NUMBER|RANK|DENSE_RANK)\s*\(", stripped, re.I)})
    parametros = sorted(set(_PARAM_RE.findall(stripped)))
    parametros = [f":{p}" for p in parametros] + [f"@{p}" for p in _AT_PARAM_RE.findall(stripped)]
    parametros = sorted(set(parametros))
    subqueries = len(re.findall(r"\(\s*SELECT\b", stripped, re.I))
    unions = len(re.findall(r"\bUNION\b", stripped, re.I))
    cases = len(re.findall(r"\bCASE\b", stripped, re.I))
    score = len(joins) * 2 + subqueries * 3 + len(metricas) + len(dimensoes) * 0.5 + len(ctes) * 1.5 + unions * 2
    tipo_semantico = "Agregação" if metricas else "Listagem"
    if tipo in {"INSERT", "UPDATE", "DELETE", "MERGE"}:
        tipo_semantico = "Mutação"
    elif tipo == "CREATE":
        tipo_semantico = "DDL"
    elif window_functions:
        tipo_semantico = "Analítica"
    elif ctes and metricas:
        tipo_semantico = "Pipeline"

    uso = {
        "select": colunas[:40],
        "where": [],
        "join": [],
        "group": dimensoes[:12],
        "order": [],
        "having": [],
    }
    column_lineage = [{"coluna": c, "origens": []} for c in colunas[:40]]

    return {
        "tipo": tipo,
        "tipo_semantico": tipo_semantico,
        "tabelas": tables,
        "tabelas_leitura": [t for t in tables if t not in set(written)],
        "tabelas_escrita": written,
        "colunas": colunas[:80],
        "metricas": metricas,
        "dimensoes": dimensoes,
        "ctes": list(dict.fromkeys(ctes)),
        "ctes_detail": [{"nome": c, "tabelas": [], "colunas": [], "column_lineage": []} for c in dict.fromkeys(ctes)],
        "joins": joins,
        "joins_count": len(joins),
        "subqueries": subqueries,
        "unions": unions,
        "window_functions": window_functions,
        "cases": cases,
        "filtros": filtros,
        "order_by": [],
        "limit": (lambda m: m.group(0) if m else None)(re.search(r"\bLIMIT\s+[^\s;]+", stripped, re.I)),
        "distinct": bool(re.search(r"\bSELECT\s+DISTINCT\b", stripped, re.I)),
        "parametros": parametros,
        "complexidade": "Baixa" if score <= 3 else "Média" if score <= 8 else "Alta",
        "complexidade_score": round(float(score), 2),
        "uso_colunas": uso,
        "column_lineage": column_lineage,
        "join_implicito": bool(_COMMA_JOIN_RE.search(stripped)),
        "parse_mode": "heuristic",
    }


def analyze_sql(sql: str, dialect: Optional[str] = None) -> Dict[str, Any]:
    raw = sql or ""
    stripped = raw.strip()
    if not stripped:
        return {"erro": "SQL vazio", "detalhe": "arquivo sem conteúdo"}

    used_dialect, trees, mode = parse_sql(stripped, preferred=dialect)
    if mode != "ast" or not trees:
        primary = heuristic_analyze(stripped)
        primary["dialect"] = used_dialect or dialect or "auto"
        primary["comentario"] = _leading_comment(stripped)
        primary["linhas"] = stripped.count("\n") + 1
        primary["bytes"] = len(stripped.encode("utf-8"))
        primary["hash"] = hashlib.sha1(stripped.encode("utf-8")).hexdigest()[:12]
        primary["statements"] = max(1, len([p for p in re.split(r";\s*\n", stripped) if p.strip()]))
        primary["parse_warning"] = "AST indisponível — extração heurística"
        names = list(primary.get("colunas") or []) + list(primary.get("tabelas") or [])
        primary["pii"] = pii_hits_from_names(names, stripped)
        return primary

    try:
        analyses = [_analyze_tree(tree) for tree in trees]
    except Exception as exc:
        warnings.warn(f"análise AST parcial falhou — {exc}", RuntimeWarning)
        primary = heuristic_analyze(stripped)
        primary["dialect"] = used_dialect or "auto"
        primary["comentario"] = _leading_comment(stripped)
        primary["linhas"] = stripped.count("\n") + 1
        primary["bytes"] = len(stripped.encode("utf-8"))
        primary["hash"] = hashlib.sha1(stripped.encode("utf-8")).hexdigest()[:12]
        primary["statements"] = len(trees)
        primary["parse_warning"] = str(exc)
        primary["pii"] = detect_pii(primary, stripped)
        return primary

    primary = analyses[0]
    all_tables: Set[str] = set()
    all_metrics: Set[str] = set()
    all_ctes: List[str] = []
    all_written: List[str] = []
    all_read: List[str] = []
    for item in analyses:
        all_tables.update(item.get("tabelas") or [])
        all_metrics.update(item.get("metricas") or [])
        all_ctes.extend(item.get("ctes") or [])
        all_written.extend(item.get("tabelas_escrita") or [])
        all_read.extend(item.get("tabelas_leitura") or [])

    primary["tabelas"] = sorted(all_tables, key=str.lower)
    primary["metricas"] = sorted(all_metrics)
    primary["ctes"] = list(dict.fromkeys(all_ctes))
    primary["tabelas_escrita"] = list(dict.fromkeys(all_written))
    primary["tabelas_leitura"] = sorted(set(all_read) - set(all_written), key=str.lower)
    primary["statements"] = len(trees)
    primary["dialect"] = used_dialect
    primary["comentario"] = _leading_comment(stripped)
    primary["linhas"] = stripped.count("\n") + 1
    primary["bytes"] = len(stripped.encode("utf-8"))
    primary["hash"] = hashlib.sha1(stripped.encode("utf-8")).hexdigest()[:12]
    primary["parse_mode"] = "ast"
    primary["parse_warning"] = None

    extra_cll = _sqlglot_lineage(stripped, used_dialect, primary.get("colunas") or [])
    if extra_cll:
        by_col = {row["coluna"].lower(): row for row in primary.get("column_lineage") or []}
        for row in extra_cll:
            slot = by_col.get(row["coluna"].lower())
            if slot and row.get("origens"):
                merged = list(dict.fromkeys((slot.get("origens") or []) + row["origens"]))
                slot["origens"] = merged[:24]
            elif row["coluna"].lower() not in by_col:
                (primary.setdefault("column_lineage", [])).append(row)

    primary["pii"] = detect_pii(primary, stripped)
    return primary
