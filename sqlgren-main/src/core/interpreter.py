"""Inferência semântica: título, domínio, tags, insights de qualidade e PII."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

from .i18n import domain_label, lista_humana, msg, normalize_locale, pii_label
from .smells import extra_smells


DOMAIN_RULES = (
    (("vacin", "imun", "covid", "dose", "calendario_vacinal"), "Vacinação"),
    (("hipertens", "pa_afer", "pressao", "k86", "k87"), "Hipertensão"),
    (("diabet", "glicemia", "hba1c"), "Diabetes"),
    (("gestant", "prenatal", "puerper"), "Saúde da mulher"),
    (("crianc", "infantil", "pediatr"), "Saúde da criança"),
    (("cidadao", "paciente", "territorio"), "Cadastro"),
    (("proced", "atend", "producao", "cbo"), "Produção"),
    (("unidade", "equipe", "cnes", "ine"), "Rede de atenção"),
    (("dim_", "tb_dim"), "Dimensão"),
    (("fat_", "tb_fat"), "Fato / DW"),
)


def _humanize_filename(path: str) -> str:
    stem = Path(path).stem
    stem = re.sub(r"(?i)^script[-_ ]?\d+", "", stem).strip("-_ ")
    stem = stem.replace("_", " ").replace("-", " ")
    stem = re.sub(r"\s+", " ", stem).strip()
    if not stem:
        return ""
    return stem[:1].upper() + stem[1:]


def infer_domain(info: Dict[str, Any], arquivo: str = "", locale: str = "pt") -> str:
    haystack = " ".join(
        [
            arquivo,
            " ".join(info.get("tabelas", [])),
            " ".join(info.get("ctes", [])),
            info.get("comentario") or "",
            info.get("titulo") or "",
        ]
    ).lower()
    for needles, label in DOMAIN_RULES:
        if any(n in haystack for n in needles):
            return domain_label(label, locale)
    pasta = Path(arquivo).parent.as_posix() if arquivo else ""
    if pasta and pasta not in {".", ""}:
        return pasta.replace("_", " ").replace("-", " ").title()
    return domain_label("Geral", locale)


def gerar_titulo(info: Dict[str, Any], arquivo: str = "", locale: str = "pt") -> str:
    locale = normalize_locale(locale)
    comment = (info.get("comentario") or "").strip()
    if comment and len(comment) >= 8:
        first = re.split(r"[.;|]", comment)[0].strip()
        if 8 <= len(first) <= 90 and not first.lower().startswith("nº"):
            return first
        if first.lower().startswith("nº") or first.lower().startswith("no "):
            return first[:80]

    named = _humanize_filename(arquivo)
    if named:
        return named

    metricas = info.get("metricas", [])
    dimensoes = info.get("dimensoes", [])
    if metricas and dimensoes:
        return msg(
            "title.metrics_by",
            locale,
            metrics=lista_humana(metricas, locale),
            dims=lista_humana(dimensoes[:3], locale),
        )
    if metricas:
        return msg("title.metrics", locale, metrics=lista_humana(metricas, locale))
    if dimensoes:
        return msg("title.dims", locale, dims=lista_humana(dimensoes[:3], locale))
    if info.get("tipo") == "UPDATE":
        return msg("title.update", locale)
    if info.get("tipo") == "INSERT":
        return msg("title.insert", locale)
    if info.get("tipo") == "DELETE":
        return msg("title.delete", locale)
    return msg("title.list", locale)


def gerar_descricao(info: Dict[str, Any], locale: str = "pt") -> str:
    locale = normalize_locale(locale)
    tipo = info.get("tipo_semantico") or info.get("tipo") or "Consulta"
    metricas = info.get("metricas", [])
    dimensoes = info.get("dimensoes", [])
    tabelas = info.get("tabelas", [])
    ctes = info.get("ctes", [])
    joins = info.get("joins_count", 0)
    partes = [msg("desc.head", locale, kind=tipo, tipo=info.get("tipo", "SQL"))]

    if ctes:
        partes.append(msg(
            "desc.ctes",
            locale,
            n=len(ctes),
            s="s" if len(ctes) != 1 else "",
            names=lista_humana(ctes[:4], locale),
        ))
    if metricas:
        partes.append(msg("desc.metrics", locale, names=lista_humana(metricas, locale)))
    if dimensoes:
        partes.append(msg("desc.dims", locale, names=lista_humana(dimensoes[:4], locale)))
    if joins:
        partes.append(msg(
            "desc.joins",
            locale,
            n=joins,
            oes="ões" if locale == "pt" and joins != 1 else ("s" if locale == "en" and joins != 1 else ""),
            s="s" if locale == "en" and joins != 1 else "",
        ))
    if tabelas:
        shown = tabelas[:5]
        extra = msg("desc.more", locale, n=len(tabelas) - 5) if len(tabelas) > 5 else ""
        partes.append(msg("desc.tables", locale, names=lista_humana(shown, locale), extra=extra))
    if info.get("window_functions"):
        partes.append(msg("desc.window", locale, names=lista_humana(info["window_functions"], locale)))
    written = info.get("tabelas_escrita") or []
    if written:
        partes.append(msg("desc.write", locale, names=lista_humana(written[:4], locale)))
    return ". ".join(partes) + "."


def gerar_tags(info: Dict[str, Any], dominio: str) -> List[str]:
    tags: List[str] = []
    if dominio and dominio != "Geral":
        tags.append(dominio)
    tags.append(info.get("tipo", "SQL"))
    tags.append(info.get("tipo_semantico", "Consulta"))
    tags.append(info.get("complexidade", "Média"))
    if info.get("ctes"):
        tags.append("CTE")
    if info.get("unions"):
        tags.append("UNION")
    if info.get("window_functions"):
        tags.append("Window")
    if info.get("distinct"):
        tags.append("DISTINCT")
    if info.get("parametros"):
        tags.append("Parametrizada")
    if (info.get("pii") or {}).get("exposto"):
        tags.append("PII")
    if info.get("parse_mode") == "heuristic":
        tags.append("Heurística")
    if info.get("tabelas_escrita"):
        tags.append("Escrita")
    return list(dict.fromkeys(tags))


def _has_header(sql: str, comentario: str) -> bool:
    if (comentario or "").strip():
        return True
    head = (sql or "").lstrip()
    return head.startswith("--") or head.startswith("/*")


def gerar_insights(info: Dict[str, Any], sql: str, locale: str = "pt") -> List[Dict[str, str]]:
    locale = normalize_locale(locale)
    insights: List[Dict[str, str]] = []
    upper = sql.upper()
    tipo = info.get("tipo")
    tabelas = info.get("tabelas", [])

    if not _has_header(sql, info.get("comentario") or ""):
        insights.append({"nivel": "alerta", "codigo": "missing-header", "mensagem": msg("missing-header", locale)})

    if re.search(r"SELECT\s+\*", sql, re.I) and tipo == "SELECT":
        insights.append({"nivel": "alerta", "codigo": "select-star", "mensagem": msg("select-star", locale)})

    if tipo in {"UPDATE", "DELETE"} and not info.get("filtros"):
        insights.append({
            "nivel": "critico",
            "codigo": "unfiltered-mutation",
            "mensagem": msg("unfiltered-mutation", locale, tipo=tipo),
        })

    if info.get("joins_count", 0) >= 6:
        insights.append({
            "nivel": "alerta",
            "codigo": "join-heavy",
            "mensagem": msg("join-heavy", locale, n=info["joins_count"]),
        })

    if info.get("subqueries", 0) >= 3:
        insights.append({"nivel": "info", "codigo": "nested-subqueries", "mensagem": msg("nested-subqueries", locale)})

    if tipo == "SELECT" and not info.get("limit") and not info.get("metricas") and info.get("joins_count", 0) >= 2:
        insights.append({"nivel": "info", "codigo": "unbounded-select", "mensagem": msg("unbounded-select", locale)})

    if info.get("complexidade") == "Alta":
        insights.append({
            "nivel": "alerta",
            "codigo": "high-complexity",
            "mensagem": msg("high-complexity", locale, score=info.get("complexidade_score")),
        })

    if not tabelas:
        insights.append({"nivel": "info", "codigo": "no-tables", "mensagem": msg("no-tables", locale)})

    if info.get("join_implicito"):
        insights.append({"nivel": "alerta", "codigo": "comma-join", "mensagem": msg("comma-join", locale)})

    if "CURRENT_DATE" in upper or "NOW()" in upper or "GETDATE" in upper:
        insights.append({
            "nivel": "info",
            "codigo": "non-deterministic-time",
            "mensagem": msg("non-deterministic-time", locale),
        })

    if info.get("parse_mode") == "heuristic":
        insights.append({"nivel": "alerta", "codigo": "heuristic-parse", "mensagem": msg("heuristic-parse", locale)})

    pii = info.get("pii") or {}
    if pii.get("exposto"):
        cols = ", ".join(sorted({
            pii_label(h.get("rotulo") or h.get("codigo"), locale) for h in pii.get("hits") or []
        })) or ("campos sensíveis" if locale == "pt" else "sensitive fields")
        extra = msg("pii-extra-literals", locale) if pii.get("literais") else ""
        insights.append({
            "nivel": "alerta",
            "codigo": "pii-exposure",
            "mensagem": msg("pii-exposure", locale, cols=cols, extra=extra),
        })

    insights.extend(extra_smells(info, sql, locale=locale))

    if not insights:
        insights.append({"nivel": "ok", "codigo": "clean", "mensagem": msg("clean", locale)})

    return insights


def interpretar(info: Dict[str, Any], arquivo: str = "", sql: str = "", locale: str = "pt") -> Dict[str, Any]:
    locale = normalize_locale(locale)
    titulo = gerar_titulo(info, arquivo, locale=locale)
    enriched = {**info, "titulo": titulo}
    dominio = infer_domain(enriched, arquivo, locale=locale)
    descricao = gerar_descricao(enriched, locale=locale)
    tags = gerar_tags(enriched, dominio)
    insights = gerar_insights(enriched, sql, locale=locale)
    pii = dict(enriched.get("pii") or {})
    if pii.get("hits"):
        pii["hits"] = [
            {**h, "rotulo": pii_label(h.get("rotulo") or h.get("codigo") or "", locale)}
            for h in pii["hits"]
        ]
    pasta = arquivo.split("/")[0] if "/" in arquivo else (arquivo.split("\\")[0] if "\\" in arquivo else "raiz")
    if pasta == arquivo:
        pasta = "raiz"
    return {
        **enriched,
        "titulo": titulo,
        "descricao": descricao,
        "dominio": dominio,
        "tags": tags,
        "insights": insights,
        "pii": pii or enriched.get("pii"),
        "dono": pasta if pasta != arquivo else "raiz",
        "tem_header": _has_header(sql, info.get("comentario") or ""),
        "locale": locale,
    }
