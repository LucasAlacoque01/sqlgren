import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

const DOMAIN_RULES = [
  [["vacin", "imun", "covid", "dose", "calendario_vacinal"], "Vacinação"],
  [["hipertens", "pa_afer", "pressao", "k86", "k87"], "Hipertensão"],
  [["diabet", "glicemia", "hba1c"], "Diabetes"],
  [["gestant", "prenatal", "puerper"], "Saúde da mulher"],
  [["crianc", "infantil", "pediatr"], "Saúde da criança"],
  [["cidadao", "paciente", "territorio"], "Cadastro"],
  [["proced", "atend", "producao", "cbo"], "Produção"],
  [["unidade", "equipe", "cnes", "ine"], "Rede de atenção"],
  [["dim_", "tb_dim"], "Dimensão"],
  [["fat_", "tb_fat"], "Fato / DW"],
];

const PII_RULES = [
  ["cns", /\b(nu_)?cns\b|cartao_sus/i, "CNS / Cartão SUS"],
  ["cpf", /\b(nu_)?cpf(_cidadao)?\b/i, "CPF"],
  ["rg", /\b(nu_)?rg\b/i, "RG"],
  ["email", /\b(e_?mail|ds_email)\b/i, "E-mail"],
  ["telefone", /\b(nu_)?(telefone|celular|fone)\b/i, "Telefone"],
  ["senha", /\b(senha|password|passwd|pwd)\b/i, "Senha"],
  ["token", /\b(token|secret|api_key)\b/i, "Token / segredo"],
];

function leadingComment(sql) {
  const lines = [];
  for (const raw of sql.split(/\r?\n/)) {
    const line = raw.trim();
    if (!line) { if (lines.length) break; continue; }
    if (line.startsWith("--")) { lines.push(line.slice(2).trim()); continue; }
    break;
  }
  return lines.join(" ").replace(/^(resumo|título|titulo)\s*:\s*/i, "").slice(0, 240);
}

function splitStatements(sql) {
  return sql.split(/;\s*(?=\S)/).map((s) => s.trim()).filter(Boolean);
}

function statementType(sql) {
  const head = sql.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^--.*$/gm, "").trim();
  const first = head.split(/\s+/)[0]?.toUpperCase() || "UNKNOWN";
  if (first === "WITH") return "SELECT";
  return ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "MERGE", "DROP"].includes(first) ? first : "SELECT";
}

function detectPii(names, sql) {
  const hits = [];
  const seen = new Set();
  for (const raw of names) {
    const text = String(raw || "");
    for (const [codigo, pattern, rotulo] of PII_RULES) {
      if (!pattern.test(text)) continue;
      const key = `${codigo}:${text.toLowerCase()}`;
      if (seen.has(key)) continue;
      seen.add(key);
      hits.push({ codigo, coluna: text, rotulo });
    }
  }
  const literais = [];
  if (/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i.test(sql)) literais.push("email-literal");
  return { hits, literais, exposto: Boolean(hits.length || literais.length), quantidade: hits.length + literais.length };
}

function extractOne(sql) {
  const ctes = [...sql.matchAll(/([A-Za-z_][\w]*)\s+AS\s*\(\s*SELECT\b/gi)].map((m) => m[1]);
  const cteSet = new Set(ctes.map((c) => c.toLowerCase()));
  const skip = new Set(["age", "extract", "date", "timestamp", "current_date", "current_timestamp", "cast", "coalesce", "nullif", "greatest", "least", "to_char", "to_date"]);
  const tables = [];
  const seenTables = new Set();
  const tableRe = /\b(?:FROM|JOIN|UPDATE|INTO|MERGE\s+INTO|DELETE\s+FROM)\s+([A-Za-z_][\w.]*)/gi;
  let match;
  while ((match = tableRe.exec(sql))) {
    const name = match[1];
    const key = name.toLowerCase();
    if (cteSet.has(key) || skip.has(key) || key.startsWith("unnest") || seenTables.has(key)) continue;
    seenTables.add(key);
    tables.push(key);
  }
  const written = [];
  const writeRe = /\b(?:INSERT\s+INTO|UPDATE|DELETE\s+FROM|MERGE\s+INTO|CREATE\s+TABLE)\s+([A-Za-z_][\w.]*)/gi;
  while ((match = writeRe.exec(sql))) written.push(match[1].toLowerCase());
  const joins = [...sql.matchAll(/\b((?:LEFT|RIGHT|FULL|INNER|CROSS)\s+)?JOIN\s+([A-Za-z_][\w.]*)/gi)]
    .map((m) => ({ tipo: `${(m[1] || "").trim().toUpperCase()} JOIN`.trim(), tabela: m[2] }));
  const metricas = [...new Set((sql.match(/\b(COUNT|SUM|AVG|MIN|MAX|ROUND)\s*\(/gi) || []).map((m) => m.replace(/\s*\($/, "").toUpperCase()))];
  const group = sql.match(/\bGROUP\s+BY\s+([^;]+?)(?:ORDER|LIMIT|HAVING|$)/i);
  const dimensoes = group ? group[1].split(",").map((s) => s.trim()).filter(Boolean) : [];
  const colunas = [];
  const select = sql.match(/\bSELECT\b([\s\S]*?)\bFROM\b/i);
  if (select) {
    select[1].split(",").forEach((part) => {
      const alias = part.match(/\bAS\s+("([^"]+)"|[\w]+)/i);
      const label = alias ? (alias[2] || alias[1]) : part.trim().split(/\s+/).pop();
      if (label && label !== "*") colunas.push(label.replace(/["']/g, ""));
    });
  }
  const whereChunk = sql.match(/\bWHERE\b([\s\S]*?)(?:GROUP|ORDER|LIMIT|$)/i);
  const filtros = (whereChunk ? whereChunk[1] : "")
    .split(/\bAND\b/i).map((s) => s.trim()).filter((s) => s && s.length < 160).slice(0, 12);
  const joinCols = [...sql.matchAll(/\bON\s+[\w.]+\.([A-Za-z_][\w]*)/gi)].map((m) => m[1]);
  const whereCols = [...(whereChunk ? whereChunk[1] : "").matchAll(/\b([A-Za-z_][\w]*)\s*(?:=|<>|!=|IN|LIKE|IS)/gi)].map((m) => m[1]);
  const parametros = [...new Set([...(sql.match(/:[A-Za-z_]\w*/g) || []), ...(sql.match(/@[A-Za-z_]\w*/g) || [])])];
  const unions = (sql.match(/\bUNION\b/gi) || []).length;
  const subqueries = (sql.match(/\(\s*SELECT\b/gi) || []).length;
  const window_functions = [...new Set((sql.match(/\b(LAG|LEAD|ROW_NUMBER|RANK|DENSE_RANK)\s*\(/gi) || []).map((m) => m.replace(/\s*\($/, "").toUpperCase()))];
  const score = joins.length * 2 + subqueries * 3 + metricas.length + dimensoes.length * 0.5 + ctes.length * 1.5 + unions * 2;
  const tipo = statementType(sql);
  let tipo_semantico = metricas.length ? "Agregação" : "Listagem";
  if (["INSERT", "UPDATE", "DELETE", "MERGE"].includes(tipo)) tipo_semantico = "Mutação";
  else if (tipo === "CREATE") tipo_semantico = "DDL";
  else if (window_functions.length) tipo_semantico = "Analítica";
  else if (ctes.length && metricas.length) tipo_semantico = "Pipeline";
  const uniqWritten = [...new Set(written)];
  const column_lineage = colunas.slice(0, 40).map((coluna) => ({
    coluna,
    origens: tables.slice(0, 3).map((t) => `${t}.${coluna}`),
  }));
  return {
    tipo,
    tipo_semantico,
    tabelas: [...new Set(tables)],
    tabelas_leitura: tables.filter((t) => !uniqWritten.includes(t)),
    tabelas_escrita: uniqWritten,
    colunas: colunas.slice(0, 80),
    metricas,
    dimensoes,
    ctes: [...new Set(ctes)],
    ctes_detail: [...new Set(ctes)].map((nome) => ({ nome, tabelas: [], colunas: [], column_lineage: [] })),
    joins,
    joins_count: joins.length,
    subqueries,
    unions,
    window_functions,
    cases: (sql.match(/\bCASE\b/gi) || []).length,
    filtros,
    order_by: [],
    limit: sql.match(/\bLIMIT\s+[^\s;]+/i)?.[0] || null,
    distinct: /\bSELECT\s+DISTINCT\b/i.test(sql),
    parametros,
    complexidade: score <= 3 ? "Baixa" : score <= 8 ? "Média" : "Alta",
    complexidade_score: Math.round(score * 100) / 100,
    dialect: "postgres",
    comentario: leadingComment(sql),
    linhas: sql.split(/\r?\n/).length,
    bytes: Buffer.byteLength(sql),
    hash: crypto.createHash("sha1").update(sql).digest("hex").slice(0, 12),
    statements: 1,
    parse_mode: "heuristic",
    uso_colunas: {
      select: colunas.slice(0, 40),
      where: [...new Set(whereCols)].slice(0, 20),
      join: [...new Set(joinCols)].slice(0, 20),
      group: dimensoes.slice(0, 12),
      order: [],
      having: [],
    },
    column_lineage,
    join_implicito: /\bFROM\s+[\w.]+(\s+\w+)?\s*,\s*[\w.]+/i.test(sql),
  };
}

function extract(sql) {
  const parts = splitStatements(sql);
  if (parts.length <= 1) {
    const one = extractOne(sql);
    one.pii = detectPii([...(one.colunas || []), ...(one.tabelas || []), ...Object.values(one.uso_colunas || {}).flat()], sql);
    one.statements = 1;
    return one;
  }
  const analyses = parts.map(extractOne);
  const primary = analyses[0];
  primary.tabelas = [...new Set(analyses.flatMap((a) => a.tabelas))];
  primary.tabelas_escrita = [...new Set(analyses.flatMap((a) => a.tabelas_escrita))];
  primary.tabelas_leitura = primary.tabelas.filter((t) => !primary.tabelas_escrita.includes(t));
  primary.ctes = [...new Set(analyses.flatMap((a) => a.ctes))];
  primary.metricas = [...new Set(analyses.flatMap((a) => a.metricas))];
  primary.joins = analyses.flatMap((a) => a.joins);
  primary.joins_count = primary.joins.length;
  primary.statements = parts.length;
  primary.pii = detectPii([...(primary.colunas || []), ...(primary.tabelas || [])], sql);
  return primary;
}

function inferDomain(info, arquivo) {
  const hay = `${arquivo} ${info.tabelas.join(" ")} ${info.ctes.join(" ")} ${info.comentario}`.toLowerCase();
  for (const [needles, label] of DOMAIN_RULES) {
    if (needles.some((n) => hay.includes(n))) return label;
  }
  const pasta = path.posix.dirname(arquivo.replaceAll("\\", "/"));
  return pasta && pasta !== "." ? pasta.replace(/[-_]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) : "Geral";
}

function insights(info, sql) {
  const out = [];
  const comentario = info.comentario || "";
  if (!comentario && !/^\s*(--|\/\*)/.test(sql)) {
    out.push({ nivel: "alerta", codigo: "missing-header", mensagem: "Arquivo sem comentário de cabeçalho." });
  }
  if (/SELECT\s+\*/i.test(sql) && info.tipo === "SELECT") out.push({ nivel: "alerta", codigo: "select-star", mensagem: "SELECT * reduz clareza de contrato e pode inflar I/O." });
  if (["UPDATE", "DELETE"].includes(info.tipo) && !info.filtros.length) out.push({ nivel: "critico", codigo: "unfiltered-mutation", mensagem: `${info.tipo} sem predicado WHERE detectado.` });
  if (info.joins_count >= 6) out.push({ nivel: "alerta", codigo: "join-heavy", mensagem: `${info.joins_count} JOINs — considere um modelo intermediário.` });
  if (info.complexidade === "Alta") out.push({ nivel: "alerta", codigo: "high-complexity", mensagem: `Score estrutural ${info.complexidade_score} — documente premissas e filtros de período.` });
  if (/\bFROM\s+[\w.]+(\s+\w+)?\s*,\s*[\w.]+/i.test(sql)) out.push({ nivel: "alerta", codigo: "comma-join", mensagem: "JOIN implícito (FROM a, b). Prefira JOIN explícito." });
  if (/CURRENT_DATE|NOW\(\)|GETDATE/i.test(sql)) out.push({ nivel: "info", codigo: "non-deterministic-time", mensagem: "Usa data/hora corrente — o resultado muda a cada execução." });
  if ((info.pii || {}).exposto) {
    const cols = [...new Set((info.pii.hits || []).map((h) => h.rotulo))].join(", ") || "campos sensíveis";
    out.push({ nivel: "alerta", codigo: "pii-exposure", mensagem: `Possível PII em ${cols}.` });
  }
  if (/INSERT\s+INTO\s+[\w.]+\s+SELECT\b/i.test(sql) && info.tipo === "INSERT") out.push({ nivel: "alerta", codigo: "insert-no-columns", mensagem: "INSERT sem lista de colunas — o contrato quebra se a tabela ganhar campo." });
  if (/\bNOT\s+IN\s*\(\s*SELECT\b/i.test(sql)) out.push({ nivel: "alerta", codigo: "not-in-subquery", mensagem: "NOT IN (SELECT …) trata NULL como desconhecido. Prefira NOT EXISTS." });
  if (info.distinct && info.joins_count >= 1) out.push({ nivel: "info", codigo: "distinct-join-fanout", mensagem: "DISTINCT após JOIN costuma esconder fan-out." });
  if (/\bUNION\b/i.test(sql) && !/\bUNION\s+ALL\b/i.test(sql)) out.push({ nivel: "info", codigo: "union-dedup", mensagem: "UNION (sem ALL) força DISTINCT implícito." });
  if (/\bCROSS\s+JOIN\b/i.test(sql)) out.push({ nivel: "alerta", codigo: "cross-join", mensagem: "CROSS JOIN explícito — volume explode." });
  if (!out.length) out.push({ nivel: "ok", codigo: "clean", mensagem: "Estrutura legível, sem sinais óbvios de risco estrutural." });
  return out;
}

function humanList(items) {
  if (!items.length) return "";
  if (items.length === 1) return items[0];
  return `${items.slice(0, -1).join(", ")} e ${items.at(-1)}`;
}

function describe(info) {
  const parts = [`${info.tipo_semantico} em ${info.tipo}`];
  if (info.ctes.length) parts.push(`organizada em ${info.ctes.length} CTE${info.ctes.length > 1 ? "s" : ""} (${humanList(info.ctes.slice(0, 4))})`);
  if (info.metricas.length) parts.push(`com cálculo de ${humanList(info.metricas)}`);
  if (info.dimensoes.length) parts.push(`agrupada por ${humanList(info.dimensoes.slice(0, 4))}`);
  if (info.joins_count) parts.push(`cruzando ${info.joins_count} junções`);
  if (info.tabelas.length) parts.push(`sobre ${humanList(info.tabelas.slice(0, 5))}`);
  if ((info.tabelas_escrita || []).length) parts.push(`escrevendo em ${humanList(info.tabelas_escrita.slice(0, 4))}`);
  return `${parts.join(". ")}.`;
}

function jaccard(a, b) {
  const A = new Set(a);
  const B = new Set(b);
  const union = new Set([...A, ...B]);
  if (!union.size) return 0;
  return [...A].filter((x) => B.has(x)).length / union.size;
}

function findTwins(list) {
  const pairs = [];
  for (let i = 0; i < list.length; i += 1) {
    for (let j = i + 1; j < list.length; j += 1) {
      const ta = list[i].tabelas.map((t) => t.toLowerCase());
      const tb = list[j].tabelas.map((t) => t.toLowerCase());
      const score = Math.min(1, jaccard(ta, tb) * 0.5
        + jaccard(list[i].metricas, list[j].metricas) * 0.2
        + jaccard((list[i].sql.toLowerCase().match(/[a-z_][a-z0-9_]*/g) || []), (list[j].sql.toLowerCase().match(/[a-z_][a-z0-9_]*/g) || [])) * 0.3
        + (list[i].dominio && list[i].dominio === list[j].dominio ? 0.08 : 0));
      if (score < 0.42) continue;
      pairs.push({
        a: list[i].id, b: list[j].id,
        titulo_a: list[i].titulo, titulo_b: list[j].titulo,
        arquivo_a: list[i].arquivo, arquivo_b: list[j].arquivo,
        score: Math.round(score * 100),
        overlap: ta.filter((t) => tb.includes(t)),
        kind: score >= 0.75 ? "gemeo" : "parecido",
        economia: score >= 0.75 ? "Provável retrabalho — unifique a regra de negócio." : "Vale revisar se uma consulta cobre a outra.",
      });
    }
  }
  return pairs.sort((x, y) => y.score - x.score).slice(0, 24);
}

function graphMetrics(tables, queries) {
  const nodes = [...tables.map((t) => t.id), ...queries.map((q) => q.id)];
  const degree = Object.fromEntries(nodes.map((n) => [n, 0]));
  for (const q of queries) {
    for (const table of q.tabelas || []) {
      const tid = `tbl:${table.toLowerCase()}`;
      if (tid in degree) degree[tid] += 1;
      if (q.id in degree) degree[q.id] += 1;
    }
  }
  const n = Math.max(1, nodes.length - 1);
  const ranked = Object.entries(degree)
    .filter(([id]) => id.startsWith("tbl:"))
    .map(([id, v]) => ({ id, score: Math.round((v / n) * 10000) / 10000 }))
    .sort((a, b) => b.score - a.score);
  return { hubs: ranked.slice(0, 10), authorities: ranked.slice(0, 10), bridges: ranked.slice(0, 6), engine: "builtin" };
}

export function walkSql(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) return walkSql(full);
    return entry.name.toLowerCase().endsWith(".sql") ? [full] : [];
  });
}

const DOMAIN_EN = {
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
};

const INSIGHT_EN = {
  "missing-header": "File has no header comment.",
  "select-star": "SELECT * weakens the contract and can inflate I/O.",
  "unfiltered-mutation": "Mutation without WHERE — risk of touching the entire table.",
  "join-heavy": "Many JOINs — consider an intermediate model.",
  "high-complexity": "High structural score — document assumptions and period filters.",
  "comma-join": "Implicit join (FROM a, b). Prefer explicit JOIN.",
  "non-deterministic-time": "Uses current date/time — the result changes on every run.",
  "pii-exposure": "Possible PII in this query. Mask before sharing.",
  "insert-no-columns": "INSERT without a column list — the contract breaks if the table gains a field.",
  "not-in-subquery": "NOT IN (SELECT …) treats NULL as unknown. Prefer NOT EXISTS.",
  "distinct-join-fanout": "DISTINCT after JOIN often hides fan-out.",
  "union-dedup": "UNION (without ALL) forces implicit DISTINCT.",
  "cross-join": "Explicit CROSS JOIN — volume explodes.",
  "clean": "Readable structure, no obvious structural risk.",
  "tabela-unica": "Tables that appear in a single query — legacy or undocumented.",
  "pii-catalog": "Queries touch potentially sensitive columns (PII).",
};

function redactSql(sql) {
  return String(sql || "")
    .replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi, "[REDACTED_EMAIL]")
    .replace(/\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b/g, "[REDACTED_ID]")
    .replace(/(senha|password|passwd|pwd|token|secret|api_key|apikey)\s*=\s*('([^']*)'|"([^"]*)")/gi, "$1'[REDACTED]'")
    .replace(/\b\d{15}\b/g, "[REDACTED_HEALTH_ID]")
    .replace(/\b\d{8,}\b/g, "[REDACTED_NUM]");
}

function redactCatalog(catalog) {
  const out = structuredClone(catalog);
  out.queries = (out.queries || []).map((q) => ({
    ...q,
    sql: redactSql(q.sql),
    sql_pretty: redactSql(q.sql_pretty),
    comentario: redactSql(q.comentario),
    filtros: (q.filtros || []).map(redactSql),
    sql_targets: Object.fromEntries(Object.entries(q.sql_targets || {}).map(([k, v]) => [k, redactSql(v)])),
  }));
  out.meta = { ...(out.meta || {}), redacted: true, shareable: true };
  return out;
}

function applyEnglish(catalog) {
  const out = structuredClone(catalog);
  out.meta.locale = "en";
  out.meta.pitch = "The team's canonical SQL archive — inventory, impact, PII and evidence. No dbt. No warehouse.";
  for (const q of out.queries || []) {
    q.dominio = DOMAIN_EN[q.dominio] || q.dominio;
    q.tags = (q.tags || []).map((t) => DOMAIN_EN[t] || t);
    q.insights = (q.insights || []).map((i) => ({
      ...i,
      mensagem: INSIGHT_EN[i.codigo] || i.mensagem,
    }));
  }
  out.twins = (out.twins || []).map((t) => ({
    ...t,
    economia: t.kind === "gemeo" ? "Likely rework — unify the business rule." : "Review whether one query already covers the other.",
  }));
  out.anomalies = (out.anomalies || []).map((a) => ({
    ...a,
    mensagem: INSIGHT_EN[a.codigo] || a.mensagem,
  }));
  const s = out.stats || {};
  out.briefing = {
    headline: "Legacy SQL inventory — what the team needs to know this week",
    para_quem: [
      "A new analyst who inherited a folder of .sql",
      "A tech lead who needs blast radius before changing a table",
      "A consultancy that must leave documentation with the client",
      "Audit / internal control",
      "A data lead living on official queries without dbt",
    ],
    dores: [
      "Knowledge lives in one person's head",
      "The same indicator exists in 2 or 3 versions",
      "Fear of changing a fact table",
      "Onboarding takes weeks just to read SQL",
      "Audit without evidence",
    ],
    achados: [
      `${s.queries || 0} queries · ${s.tabelas || 0} tables`,
      `${(out.twins || []).length} similar pairs`,
      `PII in ${s.pii || 0} query(ies) · Health ${s.saude}`,
    ],
    risco_imediato: s.criticos
      ? "There is a critical alert — fix it before promoting."
      : "No structural criticals. Prioritize hubs, twins, and PII.",
    hubs: (out.briefing || {}).hubs || [],
    gemeos: (out.briefing || {}).gemeos || [],
    proximos: [
      "Freeze the canonical query for each indicator",
      "Put the HTML in onboarding and every new .sql PR",
      "Run --check in CI",
      "Review PII columns and share a redacted catalog",
    ],
    criticos: s.criticos || 0,
  };
  return out;
}

export function buildCatalogFromEntries(entries, title = "Acervo", options = {}) {
  const queries = entries.filter((e) => (e.sql || "").trim()).map((entry, index) => {
    const sql = entry.sql.trim();
    const arquivo = String(entry.path || `query-${index + 1}.sql`).replaceAll("\\", "/");
    const info = extract(sql);
    const dominio = inferDomain(info, arquivo);
    const titulo = info.comentario && info.comentario.length >= 8
      ? info.comentario.split(/[.;|]/)[0].trim()
      : path.basename(arquivo, ".sql").replace(/[-_]/g, " ");
    const tem_header = Boolean((info.comentario || "").trim());
    const tags = [...new Set([
      dominio, info.tipo, info.tipo_semantico, info.complexidade,
      info.ctes.length ? "CTE" : null,
      info.parametros.length ? "Parametrizada" : null,
      (info.pii || {}).exposto ? "PII" : null,
      (info.tabelas_escrita || []).length ? "Escrita" : null,
    ].filter(Boolean))];
    return {
      id: `q-${String(index + 1).padStart(3, "0")}`,
      index: index + 1,
      arquivo,
      pasta: arquivo.includes("/") ? arquivo.split("/").slice(0, -1).join("/") : "raiz",
      titulo,
      descricao: describe(info),
      ...info,
      dominio,
      tags,
      insights: insights(info, sql),
      sql,
      sql_pretty: sql,
      sql_targets: {},
      dono: arquivo.includes("/") ? arquivo.split("/")[0] : "raiz",
      tem_header,
    };
  });

  const tableMap = new Map();
  for (const q of queries) {
    q.tabelas = [...new Map(q.tabelas.map((t) => [t.toLowerCase(), t])).values()];
    for (const table of q.tabelas) {
      const key = table.toLowerCase();
      if (!tableMap.has(key)) tableMap.set(key, { nome: key, queries: [], escritores: [], leitores: [] });
      const slot = tableMap.get(key);
      slot.queries.push(q.id);
      if ((q.tabelas_escrita || []).includes(key)) slot.escritores.push(q.id);
      else slot.leitores.push(q.id);
    }
  }
  const tables = [...tableMap.values()]
    .map((t) => ({ nome: t.nome, id: `tbl:${t.nome}`, uso: t.queries.length, queries: t.queries, escritores: t.escritores, leitores: t.leitores }))
    .sort((a, b) => b.uso - a.uso || a.nome.localeCompare(b.nome));

  const countBy = (key) => queries.reduce((acc, q) => { acc[q[key]] = (acc[q[key]] || 0) + 1; return acc; }, {});
  const alerts = queries.flatMap((q) => q.insights.filter((i) => ["alerta", "critico"].includes(i.nivel))).length;
  const criticos = queries.flatMap((q) => q.insights.filter((i) => i.nivel === "critico")).length;
  const piiN = queries.filter((q) => (q.pii || {}).exposto).length;
  const missingDocs = queries.filter((q) => !q.tem_header).length;
  const coverage = queries.length ? Math.round((1000 * queries.filter((q) => q.descricao && q.tabelas.length).length) / queries.length) / 10 : 100;
  const docs = queries.length ? Math.round((1000 * queries.filter((q) => q.tem_header).length) / queries.length) / 10 : 100;
  const piiPenalty = Math.min(25, piiN * 5);
  const saude = Math.max(0, Math.min(100, Math.round(
    coverage * 0.30
    + docs * 0.15
    + (100 - Math.min(40, criticos * 20)) * 0.25
    + (100 - Math.min(30, alerts * 4)) * 0.10
    + 10
    + (100 - piiPenalty) * 0.10,
  )));
  const twins = findTwins(queries);
  const impact = tables.map((table) => {
    const qs = queries.filter((q) => table.queries.includes(q.id));
    const mutacoes = qs.filter((q) => ["INSERT", "UPDATE", "DELETE", "MERGE"].includes(q.tipo)).length;
    const writers = qs.filter((q) => (q.tabelas_escrita || []).includes(table.nome));
    const writerIds = new Set(writers.map((q) => q.id));
    const impactados = qs.filter((q) => !writerIds.has(q.id)).map((q) => ({ id: q.id, titulo: q.titulo, arquivo: q.arquivo }));
    return {
      tabela: table.nome, uso: table.uso, queries: table.queries, titulos: qs.map((q) => q.titulo),
      risco: writers.length || mutacoes ? "alto" : qs.length >= 3 ? "medio" : "baixo",
      mutacoes, raio: qs.length,
      vizinhos: [...new Set(qs.flatMap((q) => q.tabelas.map((t) => t.toLowerCase())).filter((t) => t !== table.nome))].slice(0, 12),
      escritores: writers.map((q) => q.id),
      impactados,
      cascata: {
        tabela: table.nome,
        alcance: impactados.length,
        hops: impactados.length ? [{ hop: 1, rotulo: "Lê esta tabela", queries: impactados.slice(0, 12) }] : [],
      },
    };
  }).sort((a, b) => b.raio - a.raio);

  const graph = graphMetrics(tables, queries);
  const catalog = {
    meta: {
      title,
      product: "Acervo",
      version: "6.0.0",
      generated_at: new Date().toISOString(),
      dialect_default: "auto",
      locale: "pt",
      redacted: false,
      shareable: false,
      edition: "community",
      pitch: "O acervo canônico do SQL do time — inventário, impacto, PII e evidência. Sem dbt. Sem banco.",
    },
    run: { processed: queries.length, skipped: 0, failed: 0, dialect: "auto", files: entries.length },
    stats: {
      queries: queries.length, tabelas: tables.length,
      pastas: new Set(queries.map((q) => q.pasta)).size,
      dominios: new Set(queries.map((q) => q.dominio)).size,
      joins: queries.reduce((n, q) => n + q.joins_count, 0),
      ctes: queries.reduce((n, q) => n + q.ctes.length, 0),
      linhas: queries.reduce((n, q) => n + q.linhas, 0),
      alertas: alerts, criticos,
      com_cte: queries.filter((q) => q.ctes.length).length,
      complexas: queries.filter((q) => q.complexidade === "Alta").length,
      cobertura: coverage, saude,
      gemeos: twins.filter((t) => t.kind === "gemeo").length,
      parecidos: twins.length,
      hubs: impact.filter((row) => row.raio >= 2).length,
      pii: piiN,
      sem_header: missingDocs,
      heuristicas: queries.length,
    },
    distribuicao: {
      tipo: countBy("tipo"), semantico: countBy("tipo_semantico"),
      complexidade: countBy("complexidade"), dominio: countBy("dominio"), pasta: countBy("pasta"),
    },
    lineage: {
      nodes: [
        ...tables.map((t) => ({ id: t.id, kind: "table", label: t.nome })),
        ...queries.map((q) => ({ id: q.id, kind: "query", label: q.titulo, tipo: q.tipo, complexidade: q.complexidade, dominio: q.dominio })),
      ],
      edges: queries.flatMap((q) => q.tabelas.map((t) => ({
        source: `tbl:${t.toLowerCase()}`,
        target: q.id,
        rel: (q.tabelas_escrita || []).includes(t.toLowerCase()) ? "writes" : "feeds",
      }))),
      tables, hubs: tables.filter((t) => t.uso > 1).slice(0, 12),
      isolated: queries.filter((q) => !q.tabelas.length).map((q) => q.id),
      column_edges: queries.flatMap((q) => (q.column_lineage || []).flatMap((row) => (row.origens || []).map((source) => ({ query: q.id, source, target: row.coluna })))).slice(0, 400),
    },
    graph,
    twins, impact,
    briefing: {
      headline: "Inventário de SQL legado — o que o time precisa saber esta semana",
      para_quem: ["Analista novo", "Tech lead", "Consultoria", "Auditoria", "BI público / APS"],
      dores: ["SQL na cabeça de uma pessoa", "Indicador duplicado", "Medo de mudar tabela", "Onboarding lento", "Auditoria sem evidência"],
      achados: [
        `${queries.length} consultas · ${tables.length} tabelas`,
        `${twins.length} pares semelhantes`,
        `PII em ${piiN} consulta(s) · Saúde ${saude}`,
      ],
      risco_imediato: criticos ? "Há alerta crítico — trate antes de promover." : "Nenhum crítico estrutural. Priorize hubs, gêmeos e PII.",
      hubs: impact.filter((row) => row.raio >= 2).slice(0, 5),
      gemeos: twins.slice(0, 5),
      proximos: ["Congelar a query canônica", "Colocar o HTML no onboarding", "Rodar --check no CI", "Revisar colunas PII"],
      criticos,
    },
    columns: [],
    relations: [],
    anomalies: [],
    implied_keys: [],
    delta: { added: [], removed: [], changed: [], unchanged: queries.length, tables_touched: [], impacted: [] },
    mermaid: "",
    queries,
  };

  const colIndex = new Map();
  for (const q of queries) {
    const uso = q.uso_colunas || {};
    for (const [clause, cols] of Object.entries(uso)) {
      for (const col of cols || []) {
        const key = String(col).toLowerCase();
        if (!colIndex.has(key)) colIndex.set(key, { nome: col, select: 0, where: 0, join: 0, group: 0, order: 0, having: 0, queries: [], pii: false });
        const slot = colIndex.get(key);
        slot[clause] = (slot[clause] || 0) + 1;
        if (!slot.queries.includes(q.id)) slot.queries.push(q.id);
      }
    }
    for (const hit of (q.pii || {}).hits || []) {
      const key = String(hit.coluna || "").toLowerCase();
      if (colIndex.has(key)) colIndex.get(key).pii = true;
    }
  }
  catalog.columns = [...colIndex.values()].sort((a, b) => b.queries.length - a.queries.length).slice(0, 200);
  const pairMap = new Map();
  for (const q of queries) {
    const ts = [...new Set(q.tabelas.map((t) => t.toLowerCase()))].sort();
    for (let i = 0; i < ts.length; i += 1) {
      for (let j = i + 1; j < ts.length; j += 1) {
        const key = `${ts[i]}|${ts[j]}`;
        if (!pairMap.has(key)) pairMap.set(key, { a: ts[i], b: ts[j], juntos: 0, queries: [] });
        pairMap.get(key).juntos += 1;
        pairMap.get(key).queries.push(q.id);
      }
    }
  }
  catalog.relations = [...pairMap.values()].sort((a, b) => b.juntos - a.juntos).slice(0, 80);
  const singles = tables.filter((t) => t.uso === 1);
  if (singles.length) catalog.anomalies.push({ nivel: "info", codigo: "tabela-unica", mensagem: `${singles.length} tabela(s) aparecem em uma query só.` });
  if (piiN) catalog.anomalies.push({ nivel: "alerta", codigo: "pii-catalog", mensagem: `${piiN} consulta(s) tocam colunas potencialmente sensíveis (PII).` });
  catalog.mermaid = ["flowchart LR", ...queries.flatMap((q) => q.tabelas.map((t) => `  ${t.replace(/[^A-Za-z0-9_]/g, "_")} --> ${q.id.replace(/-/g, "_")}`))].join("\n");
  const impliedMap = new Map();
  for (const q of queries) {
    const names = [...(q.colunas || []), ...Object.values(q.uso_colunas || {}).flat()];
    for (const raw of names) {
      const bare = String(raw).split(".").pop().toLowerCase().replace(/["']/g, "");
      if (!/^(co_|nu_|id_|fk_|cd_)/.test(bare) || bare.length < 3) continue;
      if (!impliedMap.has(bare)) impliedMap.set(bare, { coluna: bare, tabelas: new Set(), queries: [] });
      const slot = impliedMap.get(bare);
      (q.tabelas || []).forEach((t) => slot.tabelas.add(t.toLowerCase()));
      if (!slot.queries.includes(q.id)) slot.queries.push(q.id);
    }
  }
  catalog.implied_keys = [...impliedMap.values()]
    .map((r) => ({ coluna: r.coluna, tabelas: [...r.tabelas].sort(), juntas: r.tabelas.size, queries: r.queries, evidencia: "mesmo nome de chave em tabelas distintas" }))
    .filter((r) => r.juntas >= 2)
    .sort((a, b) => b.juntas - a.juntas)
    .slice(0, 80);
  catalog.stats.colunas = catalog.columns.length;
  catalog.stats.relacoes = catalog.relations.length;
  catalog.stats.implied = catalog.implied_keys.length;
  const locale = String(options.locale || "pt").toLowerCase().startsWith("en") ? "en" : "pt";
  let out = catalog;
  if (locale === "en") out = applyEnglish(out);
  if (options.redact) out = redactCatalog(out);
  return out;
}

export function renderHtml(catalog, root = ROOT) {
  const template = fs.readFileSync(path.join(root, "templates", "front.html"), "utf8");
  const css = fs.readFileSync(path.join(root, "assets", "css", "styles.css"), "utf8");
  const js = fs.readFileSync(path.join(root, "assets", "js", "app.js"), "utf8");
  const payload = JSON.stringify(catalog).replaceAll("<", "\\u003c").replaceAll(">", "\\u003e");
  const locale = String(catalog.meta?.locale || "pt");
  const lang = locale.startsWith("en") ? "en" : "pt-BR";
  const pitch = catalog.meta?.pitch || "Acervo — static SQL observatory.";
  return template
    .replaceAll("{{TITLE}}", catalog.meta.title)
    .replaceAll("{{LANG}}", lang)
    .replaceAll("{{PITCH}}", pitch)
    .replace("/*{{CSS}}*/", css)
    .replace("{{DATA}}", payload)
    .replace("/*{{JS}}*/", js);
}

export function entriesFromDir(dir) {
  return walkSql(dir).sort((a, b) => a.localeCompare(b)).map((file) => ({
    path: path.relative(dir, file).split(path.sep).join("/"),
    sql: fs.readFileSync(file, "utf8"),
  }));
}
