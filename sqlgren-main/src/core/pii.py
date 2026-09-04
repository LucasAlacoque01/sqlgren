"""Detecção de PII / dados sensíveis em SQL estático (nomes de coluna e literais)."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List

PII_PATTERNS: tuple[tuple[str, str, str], ...] = (
    ("cns", r"\b(nu_)?cns\b|cartao_sus|cartão_sus", "CNS / Cartão SUS"),
    ("cpf", r"\b(nu_)?cpf(_cidadao|_cidadão)?\b", "CPF"),
    ("rg", r"\b(nu_)?rg\b", "RG"),
    ("email", r"\b(e_?mail|ds_email|nu_email)\b", "E-mail"),
    ("telefone", r"\b(nu_)?(telefone|celular|fone|whatsapp)\b", "Telefone"),
    ("senha", r"\b(senha|password|passwd|pwd)\b", "Senha"),
    ("token", r"\b(token|secret|api_key|apikey)\b", "Token / segredo"),
    ("nascimento", r"\b(dt_|data_)?(nascimento|birth)\b", "Data de nascimento"),
    ("endereco", r"\b(ds_)?(endereco|endereço|logradouro)\b", "Endereço"),
)

_LITERAL_EMAIL = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
_LITERAL_CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
_LITERAL_CNS = re.compile(r"\b\d{15}\b")


def _scan_names(names: Iterable[str]) -> List[Dict[str, str]]:
    hits: List[Dict[str, str]] = []
    seen = set()
    for raw in names:
        text = str(raw or "").lower()
        if not text:
            continue
        for codigo, pattern, label in PII_PATTERNS:
            if re.search(pattern, text, re.I):
                key = f"{codigo}:{text}"
                if key in seen:
                    continue
                seen.add(key)
                hits.append({"codigo": codigo, "coluna": str(raw), "rotulo": label})
    return hits


def pii_hits_from_names(names: Iterable[str], sql: str = "") -> Dict[str, Any]:
    hits = _scan_names(names)
    literals: List[str] = []
    if sql:
        if _LITERAL_EMAIL.search(sql):
            literals.append("email-literal")
        if _LITERAL_CPF.search(sql):
            literals.append("cpf-literal")
        if _LITERAL_CNS.search(sql) and re.search(r"\bcns\b", sql, re.I):
            literals.append("cns-literal")
    return {
        "hits": hits,
        "literais": literals,
        "exposto": bool(hits or literals),
        "quantidade": len(hits) + len(literals),
    }


def detect_pii(info: Dict[str, Any], sql: str = "") -> Dict[str, Any]:
    names: List[str] = []
    names.extend(info.get("colunas") or [])
    uso = info.get("uso_colunas") or {}
    for cols in uso.values():
        names.extend(cols or [])
    for row in info.get("column_lineage") or []:
        names.append(row.get("coluna") or "")
        names.extend(row.get("origens") or [])
    names.extend(info.get("tabelas") or [])
    return pii_hits_from_names(names, sql)
