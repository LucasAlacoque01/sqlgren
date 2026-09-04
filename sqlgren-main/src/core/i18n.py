"""Locale do produto (pt / en). Mensagens estáveis por código — o SQL em si não é traduzido."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

SUPPORTED = ("pt", "en")

DOMAIN_EN = {
    "Vacinação": "Vaccination",
    "Hipertensão": "Hypertension",
    "Diabetes": "Diabetes",
    "Saúde da mulher": "Women's health",
    "Saúde da criança": "Child health",
    "Cadastro": "Registry",
    "Produção": "Production",
    "Rede de atenção": "Care network",
    "Dimensão": "Dimension",
    "Fato / DW": "Fact / DW",
    "Geral": "General",
}

PII_EN = {
    "CNS / Cartão SUS": "National health ID",
    "CPF": "National ID",
    "RG": "ID card",
    "E-mail": "Email",
    "Telefone": "Phone",
    "Senha": "Password",
    "Token / segredo": "Token / secret",
    "Data de nascimento": "Date of birth",
    "Endereço": "Address",
}

MESSAGES: Dict[str, Dict[str, str]] = {
    "missing-header": {
        "pt": "Arquivo sem comentário de cabeçalho. Documente o propósito em -- Resumo: antes do SQL.",
        "en": "File has no header comment. Document the purpose with -- Summary: before the SQL.",
    },
    "select-star": {
        "pt": "SELECT * reduz clareza de contrato e pode inflar I/O. Prefira colunas explícitas.",
        "en": "SELECT * weakens the contract and can inflate I/O. Prefer explicit columns.",
    },
    "unfiltered-mutation": {
        "pt": "{tipo} sem predicado WHERE detectado. Risco de afetar a tabela inteira.",
        "en": "{tipo} without a WHERE predicate. Risk of touching the entire table.",
    },
    "join-heavy": {
        "pt": "{n} JOINs — vale revisar se um modelo intermediário reduziria custo.",
        "en": "{n} JOINs — consider whether an intermediate model would cut cost.",
    },
    "nested-subqueries": {
        "pt": "Várias subqueries. CTEs nomeadas costumam deixar a intenção mais auditável.",
        "en": "Several subqueries. Named CTEs usually make intent easier to audit.",
    },
    "unbounded-select": {
        "pt": "Listagem sem LIMIT em consulta com junções — confirme se o volume é intencional.",
        "en": "Unbounded SELECT with joins — confirm the volume is intentional.",
    },
    "high-complexity": {
        "pt": "Score estrutural {score} — documente premissas e filtros de período.",
        "en": "Structural score {score} — document assumptions and period filters.",
    },
    "no-tables": {
        "pt": "Nenhuma tabela física identificada (pode ser CTE-only, valores literais ou DDL).",
        "en": "No physical table identified (CTE-only, literals, or DDL).",
    },
    "comma-join": {
        "pt": "JOIN implícito (FROM a, b). Prefira JOIN explícito — SQLFluff e o time leem melhor.",
        "en": "Implicit join (FROM a, b). Prefer explicit JOIN — reviewers and linters read it better.",
    },
    "non-deterministic-time": {
        "pt": "Usa data/hora corrente — o resultado muda a cada execução.",
        "en": "Uses current date/time — the result changes on every run.",
    },
    "heuristic-parse": {
        "pt": "Parse AST falhou; extração heurística. Revise o dialeto ou a sintaxe.",
        "en": "AST parse failed; heuristic extraction. Check dialect or syntax.",
    },
    "pii-exposure": {
        "pt": "Possível PII em {cols}.{extra} Mascarar, parametrizar e restringir acesso ao HTML.",
        "en": "Possible PII in {cols}.{extra} Mask, parameterize, and restrict HTML access.",
    },
    "pii-extra-literals": {
        "pt": " Literais hardcoded detectados.",
        "en": " Hardcoded literals detected.",
    },
    "insert-no-columns": {
        "pt": "INSERT sem lista de colunas — o contrato quebra se a tabela ganhar campo (SQLFluff AM07).",
        "en": "INSERT without a column list — the contract breaks if the table gains a field (SQLFluff AM07).",
    },
    "unused-cte": {
        "pt": "CTE definida e não referenciada: {names}.",
        "en": "CTE defined and never referenced: {names}.",
    },
    "join-without-on": {
        "pt": "JOIN sem ON — risco de produto cartesiano (SQLFluff AM08).",
        "en": "JOIN without ON — cartesian product risk (SQLFluff AM08).",
    },
    "join-on-missing": {
        "pt": "Há JOIN e nenhum predicado ON visível. Confirme se a junção está completa.",
        "en": "JOIN present but no visible ON predicate. Confirm the join is complete.",
    },
    "not-in-subquery": {
        "pt": "NOT IN (SELECT …) trata NULL como desconhecido e some linhas. Prefira NOT EXISTS.",
        "en": "NOT IN (SELECT …) treats NULL as unknown and drops rows. Prefer NOT EXISTS.",
    },
    "distinct-join-fanout": {
        "pt": "DISTINCT após JOIN costuma esconder fan-out. Revise a chave da junção.",
        "en": "DISTINCT after JOIN often hides fan-out. Review the join key.",
    },
    "union-dedup": {
        "pt": "UNION (sem ALL) força DISTINCT implícito — caro se a intenção for só empilhar.",
        "en": "UNION (without ALL) forces implicit DISTINCT — expensive if you only meant to stack.",
    },
    "cross-join": {
        "pt": "CROSS JOIN explícito — volume explode. Documente o motivo.",
        "en": "Explicit CROSS JOIN — volume explodes. Document why.",
    },
    "clean": {
        "pt": "Estrutura legível, sem sinais óbvios de risco estrutural.",
        "en": "Readable structure, no obvious structural risk.",
    },
    "tabela-unica": {
        "pt": "{n} tabela(s) aparecem em uma query só — candidatos a legado ou a documentar.",
        "en": "{n} table(s) appear in a single query — legacy candidates or undocumented.",
    },
    "query-sem-tabela": {
        "pt": "{n} consulta(s) sem tabela física detectada.",
        "en": "{n} query(ies) with no physical table detected.",
    },
    "comma-join-catalog": {
        "pt": "{n} consulta(s) com JOIN implícito (FROM a, b).",
        "en": "{n} query(ies) with implicit JOIN (FROM a, b).",
    },
    "pii-catalog": {
        "pt": "{n} consulta(s) tocam colunas potencialmente sensíveis (PII).",
        "en": "{n} query(ies) touch potentially sensitive columns (PII).",
    },
    "undocumented": {
        "pt": "{n} arquivo(s) sem cabeçalho documental.",
        "en": "{n} file(s) without a documentary header.",
    },
    "twin.duplicate": {
        "pt": "Provável retrabalho — unifique a regra de negócio.",
        "en": "Likely rework — unify the business rule.",
    },
    "twin.review": {
        "pt": "Vale revisar se uma consulta cobre a outra.",
        "en": "Review whether one query already covers the other.",
    },
    "title.update": {"pt": "Atualização de registros", "en": "Record update"},
    "title.insert": {"pt": "Carga de registros", "en": "Record load"},
    "title.delete": {"pt": "Remoção de registros", "en": "Record deletion"},
    "title.list": {"pt": "Listagem de registros", "en": "Record listing"},
    "title.metrics_by": {"pt": "{metrics} por {dims}", "en": "{metrics} by {dims}"},
    "title.metrics": {"pt": "{metrics} dos registros", "en": "{metrics} of the records"},
    "title.dims": {"pt": "Distribuição por {dims}", "en": "Distribution by {dims}"},
    "desc.head": {"pt": "{kind} em {tipo}", "en": "{kind} in {tipo}"},
    "desc.ctes": {
        "pt": "organizada em {n} CTE{s} ({names})",
        "en": "organized into {n} CTE{s} ({names})",
    },
    "desc.metrics": {"pt": "com cálculo de {names}", "en": "computing {names}"},
    "desc.dims": {"pt": "agrupada por {names}", "en": "grouped by {names}"},
    "desc.joins": {"pt": "cruzando {n} junção{oes}", "en": "crossing {n} join{s}"},
    "desc.tables": {"pt": "sobre {names}{extra}", "en": "over {names}{extra}"},
    "desc.more": {"pt": " e mais {n}", "en": " and {n} more"},
    "desc.window": {"pt": "usando funções de janela {names}", "en": "using window functions {names}"},
    "desc.write": {"pt": "escrevendo em {names}", "en": "writing to {names}"},
    "pitch": {
        "pt": "O acervo canônico do SQL do time — inventário, impacto, PII e evidência. Sem dbt. Sem banco.",
        "en": "The team's canonical SQL archive — inventory, impact, PII and evidence. No dbt. No warehouse.",
    },
}

BRIEFING = {
    "pt": {
        "headline": "Inventário de SQL legado — o que o time precisa saber esta semana",
        "para_quem": [
            "Analista novo que herdou uma pasta de .sql e não sabe por onde começar",
            "Tech lead que precisa do raio de explosão antes de alterar uma tabela",
            "Consultoria que entrega indicadores e precisa deixar documentação no cliente",
            "Auditoria / controle interno que pede evidência do que cada consulta faz",
            "Gestor de dados que vive de queries oficiais sem dbt",
        ],
        "dores": [
            "Ninguém sabe o que cada arquivo faz — o conhecimento está na cabeça de uma pessoa",
            "O mesmo indicador existe em 2 ou 3 versões e os números não batem",
            "Mudar uma tabela de fato sem saber quais relatórios quebram",
            "Onboarding de analista leva semanas só para ler SQL",
            "Auditor pede documentação e o time monta Word na véspera",
        ],
        "risco_critico": "Há mutação sem filtro ou alerta crítico — trate antes de promover.",
        "risco_ok": "Nenhum crítico estrutural. Priorize hubs, gêmeos e exposição de PII.",
        "achados": [
            "{queries} consultas indexadas em {pastas} pastas",
            "{tabelas} tabelas tocadas · {hubs} hubs com efeito em cascata",
            "{pares} pares semelhantes · {gemeos} gêmeos (retrabalho provável)",
            "{alertas} sinais de qualidade · {criticos} críticos",
            "PII em {pii} consulta(s) · Saúde do catálogo: {saude}",
        ],
        "proximos": [
            "Congelar a query canônica de cada indicador e arquivar as cópias",
            "Colocar o HTML no onboarding e no PR de qualquer .sql novo",
            "Rodar `acervo --check` no CI para bloquear UPDATE/DELETE sem WHERE",
            "Marcar um dono por pasta (indicadores, ETL, admin)",
            "Revisar colunas PII e gerar o catálogo com --redact-pii antes de compartilhar",
        ],
    },
    "en": {
        "headline": "Legacy SQL inventory — what the team needs to know this week",
        "para_quem": [
            "A new analyst who inherited a folder of .sql and does not know where to start",
            "A tech lead who needs blast radius before changing a table",
            "A consultancy that ships indicators and must leave documentation with the client",
            "Audit / internal control that asks for evidence of what each query does",
            "A data lead living on official queries without dbt",
        ],
        "dores": [
            "Nobody knows what each file does — the knowledge lives in one person's head",
            "The same indicator exists in 2 or 3 versions and the numbers disagree",
            "Changing a fact table without knowing which reports break",
            "Analyst onboarding takes weeks just to read SQL",
            "An auditor asks for documentation and the team writes a Word file the night before",
        ],
        "risco_critico": "There is an unfiltered mutation or a critical alert — fix it before promoting.",
        "risco_ok": "No structural criticals. Prioritize hubs, twins, and PII exposure.",
        "achados": [
            "{queries} queries indexed across {pastas} folders",
            "{tabelas} tables touched · {hubs} hubs with cascade effect",
            "{pares} similar pairs · {gemeos} twins (likely rework)",
            "{alertas} quality signals · {criticos} critical",
            "PII in {pii} query(ies) · Catalog health: {saude}",
        ],
        "proximos": [
            "Freeze the canonical query for each indicator and archive the copies",
            "Put the HTML in onboarding and in the PR of every new .sql",
            "Run `acervo --check` in CI to block UPDATE/DELETE without WHERE",
            "Assign an owner per folder (indicators, ETL, admin)",
            "Review PII columns and generate the catalog with --redact-pii before sharing",
        ],
    },
}

MD_HEADINGS = {
    "pt": {
        "panorama": "Panorama",
        "indice": "Índice",
        "para_quem": "Para quem isto existe",
        "dor": "A dor",
        "achados": "Achados desta geração",
        "proximos": "Próximos passos",
        "gerado": "Gerado em",
    },
    "en": {
        "panorama": "Overview",
        "indice": "Index",
        "para_quem": "Who this is for",
        "dor": "The pain",
        "achados": "Findings from this run",
        "proximos": "Next steps",
        "gerado": "Generated at",
    },
}


def normalize_locale(value: Any) -> str:
    raw = str(value or "pt").strip().lower().replace("_", "-")
    if raw.startswith("en"):
        return "en"
    return "pt"


def msg(code: str, locale: str = "pt", **kwargs: Any) -> str:
    locale = normalize_locale(locale)
    table = MESSAGES.get(code) or {}
    text = table.get(locale) or table.get("pt") or code
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError):
            return text
    return text


def lista_humana(itens: Iterable[Any], locale: str = "pt") -> str:
    items = [str(i) for i in (itens or []) if i]
    if not items:
        return ""
    conj = "and" if normalize_locale(locale) == "en" else "e"
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} {conj} {items[1]}"
    return f"{', '.join(items[:-1])} {conj} {items[-1]}"


def domain_label(canonical: str, locale: str = "pt") -> str:
    if normalize_locale(locale) != "en":
        return canonical
    return DOMAIN_EN.get(canonical, canonical)


def pii_label(canonical: str, locale: str = "pt") -> str:
    if normalize_locale(locale) != "en":
        return canonical
    return PII_EN.get(canonical, canonical)


def pitch(locale: str = "pt") -> str:
    return msg("pitch", locale)


def briefing_copy(locale: str, stats: Dict[str, Any], twins: List[Dict[str, Any]], hubs: int) -> Dict[str, Any]:
    locale = normalize_locale(locale)
    pack = BRIEFING[locale]
    gemeos = sum(1 for t in twins if t.get("kind") == "gemeo")
    ctx = {
        "queries": stats.get("queries", 0),
        "pastas": stats.get("pastas", 0),
        "tabelas": stats.get("tabelas", 0),
        "hubs": hubs,
        "pares": len(twins),
        "gemeos": gemeos,
        "alertas": stats.get("alertas", 0),
        "criticos": stats.get("criticos", 0),
        "pii": stats.get("pii", 0),
        "saude": stats.get("saude", 0),
    }
    return {
        "headline": pack["headline"],
        "para_quem": list(pack["para_quem"]),
        "dores": list(pack["dores"]),
        "achados": [line.format(**ctx) for line in pack["achados"]],
        "risco_imediato": pack["risco_critico"] if stats.get("criticos") else pack["risco_ok"],
        "proximos": list(pack["proximos"]),
    }
