(() => {
  const raw = document.getElementById("sqldoc-data");
  let CATALOG = { meta: {}, stats: {}, distribuicao: {}, lineage: { nodes: [], edges: [], tables: [] }, queries: [] };
  try {
    CATALOG = JSON.parse(raw.textContent || "{}");
  } catch (err) {
    console.error("Catálogo inválido", err);
  }

  const QUERIES = CATALOG.queries || [];
  const STATS = CATALOG.stats || {};
  const DIST = CATALOG.distribuicao || {};
  const LINEAGE = CATALOG.lineage || { nodes: [], edges: [], tables: [] };
  const META = CATALOG.meta || {};
  const TWINS = CATALOG.twins || [];
  const IMPACT = CATALOG.impact || [];
  const BRIEFING = CATALOG.briefing || {};
  const COLUMNS = CATALOG.columns || [];
  const RELATIONS = CATALOG.relations || [];
  const ANOMALIES = CATALOG.anomalies || [];
  const MERMAID = CATALOG.mermaid || "";
  const GRAPH = CATALOG.graph || { hubs: [], authorities: [], bridges: [], engine: "builtin" };
  const IMPLIED = CATALOG.implied_keys || [];
  const DELTA = CATALOG.delta || { added: [], removed: [], changed: [], impacted: [], tables_touched: [] };
  const FAV_KEY = "acervo-favs";
  const favs = new Set(JSON.parse(localStorage.getItem(FAV_KEY) || "[]"));

  const state = {
    route: "home",
    queryId: null,
    tableId: null,
    tab: "visao",
    search: "",
    tipo: "all",
    complexidade: "all",
    dominio: "all",
    pasta: "all",
    pretty: false,
    compareA: null,
    compareB: null,
    theme: localStorage.getItem("acervo-theme") || localStorage.getItem("sqlgren-theme") || "dark",
    uiLocale: localStorage.getItem("acervo-ui-locale") || ((META.locale || "pt").toString().startsWith("en") ? "en" : "pt"),
  };

  const UI = {
    pt: {
      skip: "Ir ao conteúdo", search: "Buscar · table: col: tag:", folders: "Pastas",
      "nav.home": "Observatório", "nav.catalog": "Catálogo", "nav.lineage": "Linhagem",
      "nav.tables": "Tabelas", "nav.impact": "Impacto", "nav.twins": "Gêmeos",
      "nav.brief": "Briefing", "nav.columns": "Colunas", "nav.relations": "Relações",
      "nav.govern": "Governança", "export.sql": "Exportar SQL",
      health: "saúde do catálogo", generated: "Gerado",
      kicker: "Acervo · inventário canônico de SQL",
      healthLabel: "índice de saúde do catálogo",
      pain: "A dor", painT: "O SQL oficial vive em pastas. O conhecimento vive em pessoas. Quando a pessoa sai, o indicador some.",
      who: "Para quem", whoT: "Analista novo, tech lead, consultoria, auditoria e BI — qualquer um que precise explicar SQL sem abrir o banco.",
      solves: "O que resolve", solvesT: "Inventário, gêmeos, blast radius, colunas por cláusula, PII e um briefing que se manda para o gestor.",
      twinsB: "gêmeo(s)", twinsT: "o mesmo indicador pode estar duplicado. Abra a aba Gêmeos.",
      critB: "crítico(s)", critT: "UPDATE/DELETE sem WHERE ou falha estrutural. Bloqueie o CI com --check.",
      critOk: "Nenhum crítico estrutural.", critOkT: "Priorize hubs, gêmeos e PII.",
      piiB: "PII em", piiT: "consulta(s) — CNS, CPF e afins detectados no SQL estático.",
      redacted: "Catálogo mascarado", redactedT: "Literais de PII foram substituídos. Os sinais de governança permanecem.",
      ask: "Pergunte ao acervo",
      askHint: "Operadores iguais ao SQLShelf: table: col: tag: tipo:",
      governTitle: "Governança",
      governLede: "O que um comprador, auditor ou DPO precisa ver antes de encaminhar este HTML.",
      exec: "Nada foi executado", execT: "Acervo só lê arquivos .sql. Não há conexão, JDBC, nem warehouse.",
      share: "Compartilhamento", shareT: "Gere com --redact-pii e, no Cloud, um PIN. O ZIP leva HTML + JSON + briefing.",
      edition: "Edição Community", editionT: "MIT. Pronto para consultoria. Pro/Team são intenção comercial, não cobrança.",
      piiInv: "Inventário de PII", noPii: "Nenhuma coluna sensível detectada neste lote.",
      checks: "Checklist de venda",
    },
    en: {
      skip: "Skip to content", search: "Search · table: col: tag:", folders: "Folders",
      "nav.home": "Observatory", "nav.catalog": "Catalog", "nav.lineage": "Lineage",
      "nav.tables": "Tables", "nav.impact": "Impact", "nav.twins": "Twins",
      "nav.brief": "Briefing", "nav.columns": "Columns", "nav.relations": "Relations",
      "nav.govern": "Governance", "export.sql": "Export SQL",
      health: "catalog health", generated: "Generated",
      kicker: "Acervo · canonical SQL inventory",
      healthLabel: "catalog health index",
      pain: "The pain", painT: "Official SQL lives in folders. Knowledge lives in people. When they leave, the indicator vanishes.",
      who: "Who it is for", whoT: "New analyst, tech lead, consultancy, audit and BI — anyone who must explain SQL without opening the database.",
      solves: "What it solves", solvesT: "Inventory, twins, blast radius, columns by clause, PII and a briefing a manager can forward.",
      twinsB: "twin(s)", twinsT: "the same indicator may be duplicated. Open Twins.",
      critB: "critical", critT: "UPDATE/DELETE without WHERE or a structural failure. Block CI with --check.",
      critOk: "No structural criticals.", critOkT: "Prioritize hubs, twins and PII.",
      piiB: "PII in", piiT: "query(ies) — national IDs and similar detected in static SQL.",
      redacted: "Redacted catalog", redactedT: "PII literals were replaced. Governance signals remain.",
      ask: "Ask the archive",
      askHint: "Same operators as SQLShelf: table: col: tag: tipo:",
      governTitle: "Governance",
      governLede: "What a buyer, auditor or DPO needs to see before forwarding this HTML.",
      exec: "Nothing was executed", execT: "Acervo only reads .sql files. No connection, no JDBC, no warehouse.",
      share: "Sharing", shareT: "Generate with --redact-pii and, in Cloud, a PIN. The ZIP carries HTML + JSON + briefing.",
      edition: "Community edition", editionT: "MIT. Ready for consulting. Pro/Team are product intent, not a charge.",
      piiInv: "PII inventory", noPii: "No sensitive columns detected in this batch.",
      checks: "Sales checklist",
    },
  };

  const t = (key) => (UI[state.uiLocale] || UI.pt)[key] || UI.pt[key] || key;

  const applyChrome = () => {
    document.documentElement.lang = state.uiLocale === "en" ? "en" : "pt-BR";
    document.querySelectorAll("[data-i]").forEach((el) => {
      const key = el.getAttribute("data-i");
      if (key && t(key)) el.textContent = t(key);
    });
    const loc = $("btn-locale");
    if (loc) loc.textContent = state.uiLocale === "en" ? "EN" : "PT";
  };

  const $ = (id) => document.getElementById(id);
  const stage = $("stage");

  const esc = (value) => String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

  const toast = (msg) => {
    const el = $("toast");
    el.textContent = msg;
    el.hidden = false;
    clearTimeout(toast._t);
    toast._t = setTimeout(() => { el.hidden = true; }, 2200);
  };

  const badgeClass = (value) => {
    const v = String(value || "").toLowerCase();
    if (["select", "cte", "ok", "baixa"].includes(v)) return `badge badge-${v}`;
    if (["insert", "pipeline"].includes(v)) return "badge badge-insert";
    if (["update", "média", "media", "warn", "alerta"].includes(v)) return "badge badge-update";
    if (["delete", "alta", "critico"].includes(v)) return "badge badge-delete";
    if (["agregação", "agregacao", "analítica", "analitica"].includes(v)) return "badge badge-indigo";
    return "badge";
  };

  const byId = (id) => QUERIES.find((q) => q.id === id);

  const folders = () => {
    const map = new Map();
    QUERIES.forEach((q) => map.set(q.pasta, (map.get(q.pasta) || 0) + 1));
    return [...map.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  };

  const parseSearch = (raw) => {
    const filters = { table: [], col: [], tag: [], type: [], text: [] };
    const parts = String(raw || "").trim().split(/\s+/).filter(Boolean);
    parts.forEach((part) => {
      const m = part.match(/^(table|tabela|col|tag|type|tipo):(.+)$/i);
      if (!m) { filters.text.push(part.toLowerCase()); return; }
      const key = m[1].toLowerCase();
      const val = m[2].toLowerCase();
      if (key === "table" || key === "tabela") filters.table.push(val);
      else if (key === "col") filters.col.push(val);
      else if (key === "tag") filters.tag.push(val);
      else filters.type.push(val);
    });
    return filters;
  };

  const fuzzyScore = (hay, needle) => {
    const h = String(hay || "").toLowerCase();
    const n = String(needle || "").toLowerCase();
    if (!n) return 1;
    if (h.includes(n)) return 1;
    let hi = 0;
    let score = 0;
    for (const ch of n) {
      const idx = h.indexOf(ch, hi);
      if (idx < 0) return 0;
      score += 1 / (1 + idx - hi);
      hi = idx + 1;
    }
    return score / n.length;
  };

  const filtered = () => QUERIES.filter((q) => {
    if (state.tipo !== "all" && q.tipo !== state.tipo) return false;
    if (state.complexidade !== "all" && q.complexidade !== state.complexidade) return false;
    if (state.dominio !== "all" && q.dominio !== state.dominio) return false;
    if (state.pasta !== "all" && q.pasta !== state.pasta) return false;
    if (!state.search) return true;
    const f = parseSearch(state.search);
    if (f.table.length && !f.table.every((t) => (q.tabelas || []).some((x) => x.toLowerCase().includes(t)))) return false;
    if (f.col.length && !f.col.every((c) => [...(q.colunas || []), ...Object.values(q.uso_colunas || {}).flat()].some((x) => String(x).toLowerCase().includes(c)))) return false;
    if (f.tag.length && !f.tag.every((t) => (q.tags || []).some((x) => String(x).toLowerCase().includes(t)))) return false;
    if (f.type.length && !f.type.every((t) => String(q.tipo).toLowerCase().includes(t))) return false;
    if (!f.text.length) return true;
    const hay = [q.titulo, q.descricao, q.arquivo, q.dominio, q.sql, q.dono, ...(q.tabelas || []), ...(q.tags || [])]
      .join(" ");
    return f.text.every((term) => fuzzyScore(hay, term) > 0.12);
  });

  const toggleFav = (id) => {
    if (favs.has(id)) favs.delete(id);
    else favs.add(id);
    localStorage.setItem(FAV_KEY, JSON.stringify([...favs]));
    toast(favs.has(id) ? "Favoritada" : "Removida dos favoritos");
  };

  const ring = (value, max = 100, size = 64, color = "var(--accent)") => {
    const r = (size / 2) - 6;
    const c = 2 * Math.PI * r;
    const pct = Math.max(0, Math.min(1, value / max));
    return `<svg viewBox="0 0 ${size} ${size}" aria-hidden="true">
      <circle cx="${size/2}" cy="${size/2}" r="${r}" fill="none" stroke="var(--line)" stroke-width="5"/>
      <circle cx="${size/2}" cy="${size/2}" r="${r}" fill="none" stroke="${color}" stroke-width="5"
        stroke-linecap="round" stroke-dasharray="${c}" stroke-dashoffset="${c * (1 - pct)}"
        transform="rotate(-90 ${size/2} ${size/2})"/>
    </svg>`;
  };

  const highlightSQL = (sql) => {
    const keywords = "SELECT|FROM|WHERE|AND|OR|JOIN|INNER|LEFT|RIGHT|FULL|OUTER|ON|GROUP|BY|ORDER|HAVING|LIMIT|OFFSET|AS|DISTINCT|INSERT|INTO|VALUES|UPDATE|SET|DELETE|CREATE|ALTER|DROP|TABLE|VIEW|WITH|UNION|ALL|EXISTS|IN|NOT|NULL|IS|BETWEEN|LIKE|CASE|WHEN|THEN|ELSE|END|OVER|PARTITION|ASC|DESC|TRUE|FALSE|RETURNING";
    let out = esc(sql);
    out = out.replace(/(--.*)$/gm, '<span class="sql-cm">$1</span>');
    out = out.replace(/('(?:[^'\\]|\\.)*')/g, '<span class="sql-str">$1</span>');
    out = out.replace(/\b(\d+\.?\d*)\b/g, '<span class="sql-num">$1</span>');
    out = out.replace(new RegExp(`\\b(${keywords})\\b`, "gi"), '<span class="sql-kw">$1</span>');
    out = out.replace(/(:[A-Za-z_]\w*)/g, '<span class="sql-id">$1</span>');
    return out;
  };

  const sqlBlock = (sql, id) => {
    const q = byId(id);
    const body = state.pretty && q?.sql_pretty ? q.sql_pretty : sql;
    const rows = body.split("\n").map((line, i) =>
      `<tr><td class="ln">${i + 1}</td><td>${highlightSQL(line) || " "}</td></tr>`
    ).join("");
    return `<div class="sql-wrap">
      <div class="sql-bar">
        <div style="display:flex;align-items:center;gap:10px">
          <span class="dots"><i></i><i></i><i></i></span>
          <span>SQL · ${sql.split("\n").length} linhas</span>
        </div>
        <div style="display:flex;gap:8px">
          <button class="ghost" type="button" data-pretty="${esc(id)}">Formatar</button>
          <button class="ghost" type="button" data-copy="${esc(id)}">Copiar</button>
        </div>
      </div>
      <div class="sql-body"><table><tbody>${rows}</tbody></table></div>
    </div>`;
  };

  const unique = (key) => [...new Set(QUERIES.map((q) => q[key]).filter(Boolean))].sort();

  const formatWhen = () => {
    const rawDate = META.generated_at;
    if (!rawDate) return "Gerado agora";
    try {
      return new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(new Date(rawDate));
    } catch {
      return rawDate;
    }
  };

  const renderRail = () => {
    $("folder-tree").innerHTML = folders().map(([name, count]) =>
      `<button class="folder-item ${state.pasta === name ? "is-on" : ""}" data-folder="${esc(name)}" type="button">
        <span>${esc(name)}</span><b>${count}</b>
      </button>`
    ).join("") || `<div class="path">sem pastas</div>`;

    const health = STATS.saude || 0;
    $("health-mini").innerHTML = `${ring(health, 100, 34)}<div><strong>${health}</strong><div class="path">${t("health")}</div></div>`;
    $("generated-at").textContent = `${t("generated")} ${formatWhen()}`;
    $("brand-sub").textContent = `${STATS.queries || 0} queries · ${STATS.tabelas || 0} tabelas`;
  };

  const setCrumbs = (text) => { $("crumbs").textContent = text; };

  const setNav = (route) => {
    document.querySelectorAll(".nav-item").forEach((btn) => {
      btn.classList.toggle("is-active", btn.dataset.route === route);
    });
  };

  const bars = (obj) => {
    const entries = Object.entries(obj || {});
    const max = Math.max(1, ...entries.map(([, n]) => n));
    return entries.map(([k, n]) =>
      `<div class="bar-row"><span>${esc(k)}</span><div class="bar"><i style="width:${(n / max) * 100}%"></i></div><b>${n}</b></div>`
    ).join("") || `<div class="path">sem dados</div>`;
  };

  const viewHome = () => {
    setCrumbs(t("nav.home"));
    const hubs = (LINEAGE.tables || []).slice(0, 6);
    const heavy = [...QUERIES].sort((a, b) => (b.complexidade_score || 0) - (a.complexidade_score || 0)).slice(0, 4);
    const alerts = QUERIES.flatMap((q) => (q.insights || []).filter((i) => i.nivel !== "ok").map((i) => ({ ...i, titulo: q.titulo, id: q.id }))).slice(0, 5);
    const health = STATS.saude || 0;
    const piiN = STATS.pii || 0;
    const twinBanner = (STATS.gemeos || 0) > 0
      ? `<div class="banner"><strong>${STATS.gemeos} ${t("twinsB")}</strong> — ${t("twinsT")}</div>`
      : "";
    const critBanner = (STATS.criticos || 0) > 0
      ? `<div class="banner danger"><strong>${STATS.criticos} ${t("critB")}</strong> — ${t("critT")}</div>`
      : `<div class="banner ok"><strong>${t("critOk")}</strong> ${t("critOkT")}</div>`;
    const piiBanner = piiN
      ? `<div class="banner danger"><strong>${t("piiB")} ${piiN} ${t("piiT")}</strong></div>`
      : "";
    const redactBanner = META.redacted
      ? `<div class="banner ok"><strong>${t("redacted")}</strong> — ${t("redactedT")}</div>`
      : "";
    const deltaN = (DELTA.changed || []).length + (DELTA.added || []).length;
    const deltaBanner = deltaN
      ? `<div class="banner"><strong>PR · ${deltaN} arquivo(s) mudaram</strong> — ${(DELTA.tables_touched || []).slice(0, 6).join(", ") || "ver Impacto"} · ${(DELTA.impacted || []).length} consulta(s) no raio.</div>`
      : "";

    stage.innerHTML = `
      <section class="hero">
        <div class="panel">
          <div class="kicker">${t("kicker")}</div>
          <h1 class="display">${esc(META.title || "Acervo")}</h1>
          <p class="lede">${esc(META.pitch || t("solvesT"))}</p>
          <div class="chip-wrap" style="margin-top:18px">
            <span class="chip">sqlglot · ${esc(META.dialect_default || "auto")}</span>
            <span class="chip">${STATS.linhas || 0} linhas</span>
            <span class="chip">${STATS.parecidos || 0} pares semelhantes</span>
            <span class="chip">${STATS.hubs || 0} hubs</span>
          </div>
        </div>
        <div class="panel health-card">
          <div class="health-figure">${ring(health, 100, 168)}<strong>${health}</strong></div>
          <span>${t("healthLabel")}</span>
        </div>
      </section>
      <section class="pain-grid">
        <article class="panel"><h2>${t("pain")}</h2><p>${t("painT")}</p></article>
        <article class="panel"><h2>${t("who")}</h2><p>${t("whoT")}</p></article>
        <article class="panel"><h2>${t("solves")}</h2><p>${t("solvesT")}</p></article>
      </section>
      ${redactBanner}${critBanner}${twinBanner}${piiBanner}${deltaBanner}
      ${ANOMALIES.length ? `<section class="panel" style="margin-bottom:16px"><div class="h-row"><h2>Anomalias (SchemaSpy-style)</h2></div>${ANOMALIES.map((a) => `<div class="insight ${esc(a.nivel)}">${esc(a.mensagem)}</div>`).join("")}</section>` : ""}
      <section class="panel" style="margin-bottom:16px">
        <div class="h-row"><h2>${t("ask")}</h2></div>
        <label class="search"><input id="ask-box" placeholder="table:cidadao col:cns tag:CTE"></label>
        <div id="ask-out" class="path" style="margin-top:10px">${t("askHint")}</div>
      </section>
      <section class="kpis">
        <button class="kpi" data-route="catalog" type="button"><div class="n">${STATS.queries || 0}</div><div class="l">Queries documentadas</div></button>
        <button class="kpi" data-route="impact" type="button"><div class="n">${STATS.hubs || 0}</div><div class="l">Tabelas-hub (impacto)</div></button>
        <button class="kpi" data-route="twins" type="button"><div class="n">${STATS.parecidos || 0}</div><div class="l">Pares semelhantes</div></button>
        <button class="kpi" data-route="columns" type="button"><div class="n">${piiN}</div><div class="l">Consultas com PII</div></button>
      </section>
      <section class="grid-3">
        <article class="panel">
          <div class="h-row"><h2>Complexidade</h2></div>
          ${bars(DIST.complexidade)}
        </article>
        <article class="panel">
          <div class="h-row"><h2>Tipo de statement</h2></div>
          ${bars(DIST.tipo)}
        </article>
        <article class="panel">
          <div class="h-row"><h2>Domínios</h2></div>
          <div class="chip-wrap">
            ${Object.entries(DIST.dominio || {}).map(([k, n]) =>
              `<button class="chip" data-domain="${esc(k)}" type="button">${esc(k)} · ${n}</button>`
            ).join("")}
          </div>
        </article>
      </section>
      <section class="grid-2" style="margin-top:16px">
        <article class="panel">
          <div class="h-row"><h2>Tabelas-hub</h2><button class="linkish" data-route="tables" type="button">ver todas</button></div>
          <div class="table-rank">
            ${hubs.map((t) =>
              `<button type="button" data-table="${esc(t.nome)}"><code>${esc(t.nome)}</code><b>${t.uso} queries</b></button>`
            ).join("") || "<div class='path'>Nenhuma tabela compartilhada.</div>"}
          </div>
        </article>
        <article class="panel">
          <div class="h-row"><h2>Radar de qualidade</h2></div>
          <div class="feed">
            ${alerts.map((a) =>
              `<button class="feed-item" data-qid="${esc(a.id)}" type="button"><strong>${esc(a.titulo)}</strong>${esc(a.mensagem)}</button>`
            ).join("") || "<div class='path'>Nenhum alerta estrutural.</div>"}
          </div>
        </article>
      </section>
      <section class="panel" style="margin-top:16px">
        <div class="h-row"><h2>Mais densas</h2><button class="linkish" data-route="catalog" type="button">abrir catálogo</button></div>
        <div class="cards">
          ${heavy.map(cardHTML).join("")}
        </div>
      </section>
    `;
    const ask = $("ask-box");
    if (ask) {
      ask.addEventListener("keydown", (e) => {
        if (e.key !== "Enter") return;
        state.search = ask.value;
        go("catalog");
      });
    }
  };

  const cardHTML = (q) => `
    <button class="qcard" data-qid="${esc(q.id)}" type="button">
      <div class="score">${ring(q.complexidade_score || 0, 16, 64)}<span>${esc(q.complexidade_score)}</span></div>
      <div>
        <div class="path">${esc(q.arquivo)}</div>
        <h3>${esc(q.titulo)}</h3>
        <p>${esc(q.descricao)}</p>
        <div class="meta">
          <span class="${badgeClass(q.tipo)}">${esc(q.tipo)}</span>
          <span class="${badgeClass(q.complexidade)}">${esc(q.complexidade)}</span>
          <span class="badge">${esc(q.dominio)}</span>
          ${(q.tabelas || []).slice(0, 3).map((t) => `<span class="chip">${esc(t)}</span>`).join("")}
        </div>
      </div>
    </button>
  `;

  const viewCatalog = () => {
    setCrumbs(state.pasta === "all" ? "Catálogo" : `Catálogo / ${state.pasta}`);
    const rows = filtered();
    const tipos = unique("tipo");
    const comps = unique("complexidade");
    const doms = unique("dominio");
    stage.innerHTML = `
      <div class="toolbar">
        <label class="search">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>
          <input id="catalog-search" value="${esc(state.search)}" placeholder="Busca · table:fato col:cns tag:CTE tipo:UPDATE">
        </label>
        <select class="filter" id="f-tipo">${["all", ...tipos].map((t) => `<option ${state.tipo===t?"selected":""} value="${esc(t)}">${t==="all"?"Tipo":esc(t)}</option>`).join("")}</select>
        <select class="filter" id="f-comp">${["all", ...comps].map((t) => `<option ${state.complexidade===t?"selected":""} value="${esc(t)}">${t==="all"?"Complexidade":esc(t)}</option>`).join("")}</select>
        <select class="filter" id="f-dom">${["all", ...doms].map((t) => `<option ${state.dominio===t?"selected":""} value="${esc(t)}">${t==="all"?"Domínio":esc(t)}</option>`).join("")}</select>
      </div>
      <div class="path" style="margin-bottom:12px">${rows.length} de ${QUERIES.length} queries</div>
      <div class="cards">${rows.length ? rows.map(cardHTML).join("") : `<div class="empty">Nada encontrado com esses filtros.</div>`}</div>
    `;
    const bind = (id, key) => {
      const el = $(id);
      if (!el) return;
      el.addEventListener("change", () => { state[key] = el.value; render(); });
    };
    bind("f-tipo", "tipo");
    bind("f-comp", "complexidade");
    bind("f-dom", "dominio");
    const search = $("catalog-search");
    if (search) {
      search.addEventListener("input", (e) => {
        state.search = e.target.value;
        const rows = filtered();
        const host = document.querySelector(".cards");
        const count = document.querySelector(".toolbar + .path");
        if (count) count.textContent = `${rows.length} de ${QUERIES.length} queries`;
        if (host) host.innerHTML = rows.length ? rows.map(cardHTML).join("") : `<div class="empty">Nada encontrado com esses filtros.</div>`;
      });
    }
  };

  const viewQuery = (id) => {
    const q = byId(id);
    if (!q) { state.route = "catalog"; return viewCatalog(); }
    setCrumbs(`${q.pasta} / ${q.titulo}`);
    const related = QUERIES.filter((other) => other.id !== q.id && other.tabelas.some((t) => q.tabelas.includes(t))).slice(0, 4);
    const tab = state.tab;
    const visao = `
      <div class="facts">
        <div class="fact"><small>Statement</small><b>${esc(q.tipo)} · ${esc(q.tipo_semantico)}</b></div>
        <div class="fact"><small>Complexidade</small><b>${esc(q.complexidade)} · ${esc(q.complexidade_score)}</b></div>
        <div class="fact"><small>Dialeto</small><b>${esc(q.dialect)}</b></div>
        <div class="fact"><small>Volume</small><b>${q.linhas} linhas · ${q.joins_count} joins</b></div>
      </div>
      <p class="lede">${esc(q.descricao)}</p>
      <div class="grid-2" style="margin-top:16px">
        <article class="panel">
          <div class="h-row"><h2>Tabelas</h2></div>
          <div class="chip-wrap">${(q.tabelas.length ? q.tabelas : ["—"]).map((t) => `<button class="chip" data-table="${esc(t)}" type="button">${esc(t)}</button>`).join("")}</div>
          <div class="h-row" style="margin-top:16px"><h2>CTEs</h2></div>
          <div class="chip-wrap">${(q.ctes.length ? q.ctes : ["—"]).map((t) => `<span class="badge badge-cte">${esc(t)}</span>`).join("")}</div>
        </article>
        <article class="panel">
          <div class="h-row"><h2>Métricas e dimensões</h2></div>
          <div class="chip-wrap">${(q.metricas.length ? q.metricas : ["—"]).map((t) => `<span class="chip">${esc(t)}</span>`).join("")}</div>
          <div class="chip-wrap" style="margin-top:10px">${(q.dimensoes.length ? q.dimensoes : []).map((t) => `<span class="badge badge-insert">${esc(t)}</span>`).join("")}</div>
        </article>
      </div>
      <article class="panel" style="margin-top:16px">
        <div class="h-row"><h2>Junções</h2></div>
        ${(q.joins || []).map((j) => `<div class="bar-row"><span>${esc(j.tipo)}</span><div class="bar"><i style="width:70%"></i></div><b>${esc(j.tabela || "—")}</b></div>`).join("") || "<div class='path'>Sem JOINs.</div>"}
      </article>
      <article class="panel" style="margin-top:16px">
        <div class="h-row"><h2>Colunas projetadas</h2></div>
        <div class="chip-wrap">${(q.colunas.length ? q.colunas : ["—"]).map((c) => `<span class="chip">${esc(c)}</span>`).join("")}</div>
      </article>
    `;
    const insights = (q.insights || []).map((i) =>
      `<div class="insight ${esc(i.nivel)}"><strong>${esc(i.codigo)}</strong><div>${esc(i.mensagem)}</div></div>`
    ).join("");
    const lineageMini = renderLineageSVG(q.id);
    const twinsOf = TWINS.filter((p) => p.a === q.id || p.b === q.id);
    const relatedHTML = related.length ? `<div class="cards" style="margin-top:16px">${related.map(cardHTML).join("")}</div>` : "";
    const twinsHTML = twinsOf.length ? `<article class="panel" style="margin-top:16px"><div class="h-row"><h2>Gêmeos desta query</h2></div>${twinsOf.map((p) => `<button class="feed-item" data-qid="${esc(p.a === q.id ? p.b : p.a)}" type="button"><strong>${p.score}% · ${p.kind === "gemeo" ? "Gêmeo" : "Parecido"}</strong>${esc(p.a === q.id ? p.titulo_b : p.titulo_a)}</button>`).join("")}</article>` : "";
    const piiHTML = ((q.pii || {}).hits || []).length
      ? `<article class="panel" style="margin-top:16px"><div class="h-row"><h2>PII / dados sensíveis</h2></div>${(q.pii.hits || []).map((h) => `<span class="badge badge-delete">${esc(h.rotulo || h.codigo)} · ${esc(h.coluna)}</span>`).join(" ")}</article>`
      : "";
    const blast = (IMPACT || []).filter((row) => (q.tabelas || []).some((t) => t.toLowerCase() === String(row.tabela || "").toLowerCase()));
    const blastHTML = blast.length ? `<article class="panel" style="margin-top:16px"><div class="h-row"><h2>Blast radius das tabelas desta query</h2></div>${blast.map((row) => `<div class="feed-item"><strong>${esc(row.tabela)} · raio ${row.raio} · ${esc(row.risco)}</strong>${esc((row.titulos || []).slice(0, 4).join(" · "))}</div>`).join("")}</article>` : "";
    const cll = (q.column_lineage || []).length ? (q.column_lineage || []).map((row) =>
      `<div class="cll-row"><code>${esc(row.coluna)}</code><div>${(row.origens || []).map((o) => `<span class="chip">${esc(o)}</span>`).join(" ") || "<span class='path'>origem não resolvida</span>"}</div></div>`
    ).join("") : `<div class="path">Sem linhagem de colunas extraída.</div>`;
    const uso = q.uso_colunas || {};
    const usoHTML = ["select", "where", "join", "group", "order", "having"].map((k) =>
      `<div class="cll-row"><strong>${k.toUpperCase()}</strong><div class="chip-wrap">${((uso[k] || []).length ? uso[k] : ["—"]).map((c) => `<span class="chip">${esc(c)}</span>`).join("")}</div></div>`
    ).join("");

    stage.innerHTML = `
      <div class="detail-head">
        <div>
          <button class="ghost" data-route="catalog" type="button">← Catálogo</button>
          <h1>${esc(q.titulo)}</h1>
          <div class="meta">
            <span class="${badgeClass(q.tipo)}">${esc(q.tipo)}</span>
            <span class="${badgeClass(q.complexidade)}">${esc(q.complexidade)}</span>
            <span class="badge">${esc(q.dominio)}</span>
            ${(q.tags || []).slice(0, 6).map((t) => `<span class="chip">${esc(t)}</span>`).join("")}
            ${(q.pii || {}).exposto ? `<span class="badge badge-delete">PII</span>` : ""}
          </div>
          <div class="path" style="margin-top:8px">${esc(q.arquivo)} · ${esc(q.hash)} · ${esc(q.parse_mode || "ast")}</div>
        </div>
      </div>
      <div class="tabs">
        ${["visao", "sql", "colunas", "linhagem", "insights"].map((t) =>
          `<button class="tab ${tab===t?"is-on":""}" data-tab="${t}" type="button">${t[0].toUpperCase()+t.slice(1)}</button>`
        ).join("")}
      </div>
      <div>${
        tab === "sql" ? sqlBlock(q.sql, q.id)
        : tab === "colunas" ? `<div class="panel"><div class="h-row"><h2>Linhagem de colunas (CLL)</h2></div>${cll}<div class="h-row" style="margin-top:18px"><h2>Uso por cláusula</h2></div>${usoHTML}</div>`
        : tab === "linhagem" ? `<div class="panel">${lineageMini}${blastHTML}${relatedHTML}</div>`
        : tab === "insights" ? insights + twinsHTML + piiHTML
        : visao + twinsHTML + blastHTML + piiHTML
      }</div>
    `;
  };

  const lcsDiff = (left, right) => {
    const A = String(left || "").split("\n");
    const B = String(right || "").split("\n");
    const n = A.length;
    const m = B.length;
    const dp = Array.from({ length: n + 1 }, () => new Uint16Array(m + 1));
    for (let i = 1; i <= n; i += 1) {
      for (let j = 1; j <= m; j += 1) {
        dp[i][j] = A[i - 1] === B[j - 1] ? dp[i - 1][j - 1] + 1 : Math.max(dp[i - 1][j], dp[i][j - 1]);
      }
    }
    const rows = [];
    let i = n;
    let j = m;
    while (i > 0 && j > 0) {
      if (A[i - 1] === B[j - 1]) {
        rows.push({ kind: "ctx", a: A[i - 1], b: B[j - 1] });
        i -= 1; j -= 1;
      } else if (dp[i - 1][j] >= dp[i][j - 1]) {
        rows.push({ kind: "del", a: A[i - 1], b: "" });
        i -= 1;
      } else {
        rows.push({ kind: "add", a: "", b: B[j - 1] });
        j -= 1;
      }
    }
    while (i > 0) { rows.push({ kind: "del", a: A[i - 1], b: "" }); i -= 1; }
    while (j > 0) { rows.push({ kind: "add", a: "", b: B[j - 1] }); j -= 1; }
    return rows.reverse();
  };

  const renderDiff = (aSql, bSql) => {
    const rows = lcsDiff(aSql, bSql);
    return `<table class="diff-table"><tbody>${rows.map((row, idx) => {
      const cls = row.kind === "add" ? "diff-add" : row.kind === "del" ? "diff-del" : "diff-ctx";
      const text = row.kind === "add" ? row.b : row.a;
      const mark = row.kind === "add" ? "+" : row.kind === "del" ? "−" : " ";
      return `<tr class="${cls}"><td class="diff-ln">${idx + 1}</td><td>${mark} ${highlightSQL(text) || " "}</td></tr>`;
    }).join("")}</tbody></table>`;
  };

  const forceGraphSVG = (focusQuery = null, focusTable = null) => {
    const tables = (LINEAGE.tables || []).slice(0, 40);
    const queries = QUERIES.slice(0, 40);
    if (!tables.length && !queries.length) return `<div class="empty">Sem linhagem para desenhar.</div>`;
    const W = 1100;
    const H = 640;
    const nodes = [
      ...tables.map((t) => ({ id: t.id, label: t.nome, kind: "table", x: 180 + Math.random() * 200, y: 80 + Math.random() * 480 })),
      ...queries.map((q) => ({ id: q.id, label: (q.titulo || q.id).slice(0, 28), kind: "query", x: 620 + Math.random() * 280, y: 60 + Math.random() * 520 })),
    ];
    const pos = new Map(nodes.map((n) => [n.id, n]));
    const links = (LINEAGE.edges || []).filter((e) => pos.has(e.source) && pos.has(e.target));
    for (let step = 0; step < 90; step += 1) {
      for (let i = 0; i < nodes.length; i += 1) {
        for (let j = i + 1; j < nodes.length; j += 1) {
          const a = nodes[i];
          const b = nodes[j];
          let dx = a.x - b.x;
          let dy = a.y - b.y;
          let dist = Math.hypot(dx, dy) || 1;
          const force = 420 / (dist * dist);
          dx = (dx / dist) * force;
          dy = (dy / dist) * force;
          a.x += dx; a.y += dy; b.x -= dx; b.y -= dy;
        }
      }
      for (const e of links) {
        const a = pos.get(e.source);
        const b = pos.get(e.target);
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const dist = Math.hypot(dx, dy) || 1;
        const pull = (dist - 160) * 0.03;
        a.x += (dx / dist) * pull;
        a.y += (dy / dist) * pull;
        b.x -= (dx / dist) * pull;
        b.y -= (dy / dist) * pull;
      }
      for (const n of nodes) {
        n.x += (W / 2 - n.x) * 0.01;
        n.y += (H / 2 - n.y) * 0.01;
        n.x = Math.max(40, Math.min(W - 40, n.x));
        n.y = Math.max(24, Math.min(H - 24, n.y));
      }
    }
    const hotTables = new Set();
    const hotQueries = new Set();
    if (focusQuery) {
      hotQueries.add(focusQuery);
      links.forEach((e) => { if (e.target === focusQuery) hotTables.add(e.source); });
    }
    if (focusTable) {
      const tid = focusTable.startsWith("tbl:") ? focusTable : `tbl:${focusTable.toLowerCase()}`;
      hotTables.add(tid);
      links.forEach((e) => { if (e.source === tid) hotQueries.add(e.target); });
    }
    const edgeSVG = links.map((e) => {
      const a = pos.get(e.source);
      const b = pos.get(e.target);
      const hot = hotTables.has(e.source) || hotQueries.has(e.target);
      return `<line class="g-edge ${hot ? "is-hot" : ""}" x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}" opacity="${hotTables.size && !hot ? 0.15 : 0.7}"/>`;
    }).join("");
    const nodeSVG = nodes.map((n) => {
      const hot = n.kind === "table" ? (!hotTables.size || hotTables.has(n.id)) : (!hotQueries.size || hotQueries.has(n.id));
      const attr = n.kind === "table" ? `data-table="${esc(n.label)}"` : `data-qid="${esc(n.id)}"`;
      const r = n.kind === "table" ? 8 : 7;
      const cls = n.kind === "table" ? "g-table" : "g-query";
      return `<g class="g-node" ${attr} opacity="${hot ? 1 : 0.28}">
        <circle class="${cls}" cx="${n.x}" cy="${n.y}" r="${r}"/>
        <text class="g-label" x="${n.x + 12}" y="${n.y + 4}">${esc(n.label)}</text>
      </g>`;
    }).join("");
    return `<div class="graph-wrap"><svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet">${edgeSVG}${nodeSVG}</svg></div>
      <div class="graph-legend"><span><i style="background:var(--accent)"></i>Tabela</span><span><i style="background:var(--accent-2)"></i>Query</span><span>${GRAPH.engine || "builtin"} · ${(LINEAGE.edges || []).length} arestas</span></div>`;
  };

  const renderLineageSVG = (focusQuery = null, focusTable = null) => forceGraphSVG(focusQuery, focusTable);

  const viewLineage = () => {
    setCrumbs("Linhagem");
    stage.innerHTML = `
      <div class="h-row">
        <div>
          <div class="kicker">Grafo tabela → query</div>
          <h2 style="margin:6px 0 0;font-family:var(--display);font-size:28px;letter-spacing:-.04em">Como o SQL se toca</h2>
        </div>
        <span class="chip">${(LINEAGE.edges || []).length} arestas · ${GRAPH.engine || "builtin"}</span>
      </div>
      ${renderLineageSVG()}
      ${MERMAID ? `<div class="chip-wrap" style="margin-top:12px"><button class="ghost" id="btn-mermaid" type="button">Copiar Mermaid (GitHub / Notion)</button></div>` : ""}
    `;
    $("btn-mermaid")?.addEventListener("click", () => {
      navigator.clipboard.writeText(MERMAID).then(() => toast("Mermaid copiado"));
    });
  };

  const viewColumns = () => {
    setCrumbs("Colunas · uso por cláusula");
    stage.innerHTML = `
      <div class="h-row"><div><div class="kicker">SQLPrism / clgraph</div><h2 style="margin:6px 0 0;font-family:var(--display);font-size:28px;letter-spacing:-.04em">Onde cada coluna aparece</h2></div>
        <div><button class="ghost" type="button" data-export-csv="columns">Exportar CSV</button> <span class="chip">${COLUMNS.length} colunas</span></div>
      </div>
      <p class="lede">SELECT, WHERE, JOIN, GROUP — o tipo de uso que o grep não distingue. Badge PII marca campos sensíveis.</p>
      <div class="panel" style="padding:8px 16px;margin-top:16px">
        <table class="data-table" id="col-table">
          <thead><tr>
            <th data-sort="nome">Coluna</th>
            <th data-sort="select">SELECT</th>
            <th data-sort="where">WHERE</th>
            <th data-sort="join">JOIN</th>
            <th data-sort="group">GROUP</th>
            <th data-sort="queries">Queries</th>
            <th>PII</th>
          </tr></thead>
          <tbody>
            ${COLUMNS.slice(0, 80).map((c) => `<tr data-col="${esc(c.nome)}"><td><code>${esc(c.nome)}</code></td><td>${c.select || 0}</td><td>${c.where || 0}</td><td>${c.join || 0}</td><td>${c.group || 0}</td><td>${(c.queries || []).length}</td><td>${c.pii ? '<span class="badge badge-delete">PII</span>' : "—"}</td></tr>`).join("")}
          </tbody>
        </table>
      </div>
    `;
    bindSort("col-table");
  };

  const viewRelations = () => {
    setCrumbs("Relações implícitas");
    stage.innerHTML = `
      <div class="h-row"><div><div class="kicker">SchemaSpy sem banco</div><h2 style="margin:6px 0 0;font-family:var(--display);font-size:28px;letter-spacing:-.04em">Tabelas que viajam juntas</h2></div><span class="chip">${RELATIONS.length} pares</span></div>
      <p class="lede">Se duas tabelas aparecem na mesma query, existe uma relação de negócio — mesmo sem FK. Abaixo, chaves com o mesmo nome em tabelas distintas (o que o SchemaSpy chama de implied relationship).</p>
      ${IMPLIED.length ? `<div class="panel" style="padding:8px 16px;margin:16px 0">
        <div class="h-row"><h2>Chaves implícitas</h2><span class="chip">${IMPLIED.length}</span></div>
        <table class="data-table">
          <thead><tr><th>Coluna</th><th>Tabelas</th><th>Queries</th></tr></thead>
          <tbody>
            ${IMPLIED.slice(0, 40).map((k) => `<tr data-col="${esc(k.coluna)}"><td><code>${esc(k.coluna)}</code></td><td>${(k.tabelas || []).map((t) => `<button class="linkish" data-table="${esc(t)}" type="button">${esc(t)}</button>`).join(" · ")}</td><td>${(k.queries || []).length}</td></tr>`).join("")}
          </tbody>
        </table>
      </div>` : ""}
      <div class="panel" style="padding:8px 16px;margin-top:16px">
        <table class="data-table">
          <thead><tr><th>Tabela A</th><th>Tabela B</th><th>Juntas</th></tr></thead>
          <tbody>
            ${RELATIONS.map((r) => `<tr><td><button class="linkish" data-table="${esc(r.a)}" type="button">${esc(r.a)}</button></td><td><button class="linkish" data-table="${esc(r.b)}" type="button">${esc(r.b)}</button></td><td>${r.juntos}</td></tr>`).join("")}
          </tbody>
        </table>
      </div>
    `;
  };

  const viewCompare = () => {
    const a = byId(state.compareA);
    const b = byId(state.compareB);
    if (!a || !b) { state.route = "twins"; return viewTwins(); }
    setCrumbs("Comparar gêmeos");
    const cell = (q) => `<article class="panel"><div class="path">${esc(q.arquivo)}</div><h2>${esc(q.titulo)}</h2><div class="meta"><span class="${badgeClass(q.tipo)}">${esc(q.tipo)}</span><span class="${badgeClass(q.complexidade)}">${esc(q.complexidade)}</span></div><p class="lede">${esc(q.descricao)}</p><div class="chip-wrap">${(q.tabelas || []).map((t) => `<span class="chip">${esc(t)}</span>`).join("")}</div></article>`;
    stage.innerHTML = `
      <div class="grid-2">${cell(a)}${cell(b)}</div>
      <article class="panel" style="margin-top:16px">
        <div class="h-row"><h2>Diff estrutural (linha a linha)</h2>
          <button class="ghost" type="button" data-export-csv="twins">CSV do par</button>
        </div>
        <div class="sql-wrap"><div class="sql-body">${renderDiff(a.sql, b.sql)}</div></div>
      </article>
    `;
  };

  const viewTables = () => {
    setCrumbs("Tabelas");
    const tables = LINEAGE.tables || [];
    stage.innerHTML = `
      <div class="h-row"><h2>Índice de tabelas</h2><div><button class="ghost" type="button" data-export-csv="tables">CSV</button> <span class="chip">${tables.length} distintas</span></div></div>
      <div class="panel" style="padding:8px 16px">
        <table class="data-table" id="tbl-table">
          <thead><tr><th data-sort="nome">Tabela</th><th data-sort="uso">Uso</th><th data-sort="queries">Queries</th></tr></thead>
          <tbody>
            ${tables.map((t) => `<tr data-table="${esc(t.nome)}"><td><code>${esc(t.nome)}</code></td><td>${t.uso}</td><td>${t.queries.length}</td></tr>`).join("")}
          </tbody>
        </table>
      </div>
    `;
    bindSort("tbl-table");
  };

  const viewTable = (name) => {
    state.search = name;
    state.pasta = "all";
    state.route = "catalog";
    viewCatalog();
  };

  const viewImpact = () => {
    setCrumbs("Impacto · raio de explosão");
    const rows = IMPACT.length ? IMPACT : (LINEAGE.tables || []).map((t) => ({
      tabela: t.nome, raio: t.uso, risco: t.uso >= 3 ? "medio" : "baixo", mutacoes: 0, titulos: [], queries: t.queries,
    }));
    stage.innerHTML = `
      <div class="h-row">
        <div>
          <div class="kicker">Antes de alterar uma tabela</div>
          <h2 style="margin:6px 0 0;font-family:var(--display);font-size:28px;letter-spacing:-.04em">O que quebra se isto mudar</h2>
        </div>
        <span class="chip">${rows.length} tabelas</span>
      </div>
      <p class="lede">A pergunta que SQLPrism cobra caro: blast radius e cascata multi-hop. Aqui, sem DuckDB e sem warehouse.</p>
      ${(DELTA.changed || []).length || (DELTA.added || []).length ? `<div class="banner"><strong>Delta vs baseline</strong> — ${(DELTA.changed || []).length} alterada(s), ${(DELTA.added || []).length} nova(s), ${(DELTA.impacted || []).length} no raio. Tabelas: ${esc((DELTA.tables_touched || []).slice(0, 8).join(", ") || "—")}</div>` : ""}
      <section class="grid-3" style="margin-bottom:16px">
        <article class="panel"><div class="h-row"><h2>Hubs (centralidade)</h2></div>${(GRAPH.hubs || []).slice(0, 6).map((h) => `<div class="bar-row"><span>${esc((h.id || "").replace("tbl:", ""))}</span><div class="bar"><i style="width:${Math.min(100, (h.score || 0) * 100)}%"></i></div><b>${h.score}</b></div>`).join("") || "<div class='path'>sem métricas</div>"}</article>
        <article class="panel"><div class="h-row"><h2>Authorities</h2></div>${(GRAPH.authorities || []).slice(0, 6).map((h) => `<div class="bar-row"><span>${esc((h.id || "").replace("tbl:", ""))}</span><div class="bar"><i style="width:${Math.min(100, (h.score || 0) * 100)}%"></i></div><b>${h.score}</b></div>`).join("") || "<div class='path'>sem métricas</div>"}</article>
        <article class="panel"><div class="h-row"><h2>Bridges</h2></div>${(GRAPH.bridges || []).slice(0, 6).map((h) => `<div class="bar-row"><span>${esc((h.id || "").replace("tbl:", ""))}</span><div class="bar"><i style="width:${Math.min(100, (h.score || 0) * 100)}%"></i></div><b>${h.score}</b></div>`).join("") || "<div class='path'>sem pontes</div>"}</article>
      </section>
      <div class="panel" style="padding:8px 16px;margin-top:16px">
        <div class="h-row"><h2>Raio por tabela</h2><button class="ghost" type="button" data-export-csv="impact">CSV</button></div>
        <table class="data-table" id="impact-table">
          <thead><tr><th data-sort="tabela">Tabela</th><th data-sort="raio">Raio</th><th>Risco</th><th data-sort="mutacoes">Mutações</th><th>Consultas atingidas</th></tr></thead>
          <tbody>
            ${rows.map((row) => `
              <tr data-table="${esc(row.tabela)}">
                <td><code>${esc(row.tabela)}</code></td>
                <td>${row.raio || row.uso || 0}</td>
                <td><span class="${badgeClass(row.risco === "alto" ? "alta" : row.risco === "medio" ? "media" : "baixa")}">${esc(row.risco || "baixo")}</span></td>
                <td>${row.mutacoes || 0}</td>
                <td>${esc((row.titulos || []).slice(0, 3).join(" · ") || "—")}</td>
              </tr>`).join("")}
          </tbody>
        </table>
      </div>
      <div class="panel" style="margin-top:16px">
        <div class="h-row"><h2>Cascata (até 3 hops)</h2></div>
        ${rows.filter((r) => (r.cascata || {}).alcance).slice(0, 6).map((row) => `
          <div class="feed-item">
            <strong>${esc(row.tabela)} · alcance ${(row.cascata || {}).alcance || 0}</strong>
            ${(row.cascata.hops || []).map((h) => `${esc(h.rotulo)}: ${(h.queries || []).map((q) => q.titulo).slice(0, 3).join(" · ") || (h.tabelas || []).join(", ") || "—"}`).join(" · ")}
          </div>`).join("") || "<div class='path'>Nenhuma cascata além do raio direto.</div>"}
      </div>
    `;
    bindSort("impact-table");
  };

  const viewTwins = () => {
    setCrumbs("Gêmeos · retrabalho");
    stage.innerHTML = `
      <div class="h-row">
        <div>
          <div class="kicker">O mesmo indicador, duas pastas</div>
          <h2 style="margin:6px 0 0;font-family:var(--display);font-size:28px;letter-spacing:-.04em">Consultas que se repetem</h2>
        </div>
        <span class="chip">${TWINS.length} pares</span>
      </div>
      <p class="lede">Times perdem semanas reescrevendo o que já existe. Gêmeos ≥ 75% de sobreposição estrutural.</p>
      <div class="cards" style="margin-top:16px">
        ${TWINS.length ? TWINS.map((pair) => `
          <article class="twin-card">
            <div class="twin-score">${pair.score}<small>%</small></div>
            <div>
              <div class="meta"><span class="${badgeClass(pair.kind === "gemeo" ? "alta" : "media")}">${pair.kind === "gemeo" ? "Gêmeo" : "Parecido"}</span></div>
              <button class="linkish" data-qid="${esc(pair.a)}" type="button">${esc(pair.titulo_a)}</button>
              <div class="path">${esc(pair.arquivo_a)}</div>
              <button class="linkish" data-qid="${esc(pair.b)}" type="button">${esc(pair.titulo_b)}</button>
              <div class="path">${esc(pair.arquivo_b)}</div>
              <p>${esc(pair.economia)}</p>
              <div class="chip-wrap">${(pair.overlap || []).slice(0, 6).map((t) => `<span class="chip">${esc(t)}</span>`).join("")}</div>
              <button class="ghost" data-compare="${esc(pair.a)}|${esc(pair.b)}" type="button" style="margin-top:10px">Comparar lado a lado</button>
            </div>
          </article>
        `).join("") : `<div class="empty">Nenhum par semelhante neste lote — ótimo sinal, ou o corpus ainda é pequeno.</div>`}
      </div>
    `;
  };

  const viewBrief = () => {
    setCrumbs("Briefing executivo");
    const brief = BRIEFING;
    stage.innerHTML = `
      <article class="brief panel">
        <div class="kicker">Para mandar ao gestor · auditor · cliente</div>
        <h1 class="display" style="font-size:clamp(1.8rem,3vw,2.6rem)">${esc(brief.headline || "Briefing do catálogo")}</h1>
        <p class="lede"><strong>${esc(brief.risco_imediato || "")}</strong></p>
        <div class="grid-2" style="margin-top:22px">
          <div>
            <h2>A dor que isto resolve</h2>
            <ul>${(brief.dores || []).map((d) => `<li>${esc(d)}</li>`).join("")}</ul>
          </div>
          <div>
            <h2>Para quem</h2>
            <ul>${(brief.para_quem || []).map((d) => `<li>${esc(d)}</li>`).join("")}</ul>
          </div>
        </div>
        <h2>Achados desta geração</h2>
        <ul>${(brief.achados || []).map((d) => `<li>${esc(d)}</li>`).join("")}</ul>
        <h2>Próximos passos</h2>
        <ul>${(brief.proximos || []).map((d) => `<li>${esc(d)}</li>`).join("")}</ul>
        <div class="chip-wrap" style="margin-top:18px">
          <button class="ghost" id="btn-brief-copy" type="button">Copiar briefing</button>
          <button class="ghost" data-route="twins" type="button">Ver gêmeos</button>
          <button class="ghost" data-route="impact" type="button">Ver impacto</button>
        </div>
      </article>
    `;
    $("btn-brief-copy")?.addEventListener("click", () => {
      const text = [
        brief.headline, "", brief.risco_imediato, "",
        "Achados:", ...(brief.achados || []).map((d) => `• ${d}`), "",
        "Próximos:", ...(brief.proximos || []).map((d) => `• ${d}`),
      ].join("\n");
      navigator.clipboard.writeText(text).then(() => toast("Briefing copiado"));
    });
  };

  const viewGovern = () => {
    setCrumbs(t("nav.govern"));
    const piiQueries = QUERIES.filter((q) => (q.pii || {}).exposto);
    const hits = piiQueries.flatMap((q) => (q.pii.hits || []).map((h) => ({
      ...h, id: q.id, titulo: q.titulo, arquivo: q.arquivo,
    })));
    const checks = state.uiLocale === "en" ? [
      ["No SQL executed", "true"],
      ["PII literals redacted", META.redacted ? "true" : "review"],
      ["Critical mutations", (STATS.criticos || 0) === 0 ? "true" : "block"],
      ["Headers present", (STATS.sem_header || 0) === 0 ? "true" : "review"],
      ["Locale declared", META.locale || "pt"],
    ] : [
      ["SQL não executado", "true"],
      ["Literais de PII mascarados", META.redacted ? "true" : "revisar"],
      ["Mutações críticas", (STATS.criticos || 0) === 0 ? "true" : "bloquear"],
      ["Cabeçalhos presentes", (STATS.sem_header || 0) === 0 ? "true" : "revisar"],
      ["Idioma declarado", META.locale || "pt"],
    ];
    stage.innerHTML = `
      <section class="hero">
        <div class="panel">
          <div class="kicker">${esc(META.edition || "community")} · v${esc(META.version || "")}</div>
          <h1 class="display">${t("governTitle")}</h1>
          <p class="lede">${t("governLede")}</p>
        </div>
      </section>
      <section class="pain-grid">
        <article class="panel"><h2>${t("exec")}</h2><p>${t("execT")}</p></article>
        <article class="panel"><h2>${t("share")}</h2><p>${t("shareT")}</p></article>
        <article class="panel"><h2>${t("edition")}</h2><p>${t("editionT")}</p></article>
      </section>
      <section class="panel" style="margin-bottom:16px">
        <div class="h-row"><h2>${t("checks")}</h2></div>
        ${checks.map(([k, v]) => `<div class="bar-row"><span>${esc(k)}</span><b>${esc(v)}</b></div>`).join("")}
      </section>
      <section class="panel">
        <div class="h-row"><h2>${t("piiInv")}</h2><span class="chip">${piiQueries.length}</span></div>
        ${hits.length ? `<table class="grid"><thead><tr><th>PII</th><th>col</th><th>query</th><th>file</th></tr></thead><tbody>
          ${hits.slice(0, 40).map((h) => `<tr data-qid="${esc(h.id)}"><td>${esc(h.rotulo || h.codigo)}</td><td>${esc(h.coluna)}</td><td>${esc(h.titulo)}</td><td class="path">${esc(h.arquivo)}</td></tr>`).join("")}
        </tbody></table>` : `<div class="empty">${t("noPii")}</div>`}
      </section>
    `;
  };

  function render() {
    applyChrome();
    renderRail();
    const navRoute = state.route === "query" ? "catalog" : state.route === "table" ? "tables" : state.route;
    setNav(navRoute);
    if (state.route === "home") viewHome();
    else if (state.route === "catalog") viewCatalog();
    else if (state.route === "lineage") viewLineage();
    else if (state.route === "tables") viewTables();
    else if (state.route === "impact") viewImpact();
    else if (state.route === "twins") viewTwins();
    else if (state.route === "brief") viewBrief();
    else if (state.route === "columns") viewColumns();
    else if (state.route === "relations") viewRelations();
    else if (state.route === "govern") viewGovern();
    else if (state.route === "compare") viewCompare();
    else if (state.route === "query") viewQuery(state.queryId);
    else if (state.route === "table") viewTable(state.tableId);
    applyTheme();
  }

  function go(route, extra = {}) {
    Object.assign(state, extra, { route });
    if (route !== "query") state.tab = "visao";
    const hash = route === "home" ? "#/"
      : route === "query" ? `#/q/${state.queryId}`
      : route === "table" ? `#/table/${encodeURIComponent(state.tableId)}`
      : route === "compare" ? `#/compare/${state.compareA}/${state.compareB}`
      : `#/${route}`;
    if (location.hash !== hash) history.pushState({}, "", hash);
    render();
    $("rail").classList.remove("is-open");
    $("scrim").hidden = true;
  }

  function parseHash() {
    const h = (location.hash || "#/").replace(/^#/, "");
    const parts = h.split("/").filter(Boolean);
    if (!parts.length) return go("home");
    if (parts[0] === "q") return go("query", { queryId: parts[1] });
    if (parts[0] === "table") return go("table", { tableId: decodeURIComponent(parts[1] || "") });
    if (parts[0] === "compare") return go("compare", { compareA: parts[1], compareB: parts[2] });
    if (["catalog", "lineage", "tables", "impact", "twins", "brief", "columns", "relations", "govern"].includes(parts[0])) return go(parts[0]);
    return go("home");
  }

  function applyTheme() {
    document.documentElement.dataset.theme = state.theme;
    localStorage.setItem("acervo-theme", state.theme);
  }

  function debounce(fn, ms) {
    let t;
    return (...args) => {
      clearTimeout(t);
      t = setTimeout(() => fn(...args), ms);
    };
  }

  const paletteItems = () => {
    const q = ($("palette-input")?.value || "").toLowerCase();
    const actions = [
      { kind: "Ir", label: "Observatório", run: () => go("home") },
      { kind: "Ir", label: "Catálogo", run: () => go("catalog") },
      { kind: "Ir", label: "Linhagem", run: () => go("lineage") },
      { kind: "Ir", label: "Tabelas", run: () => go("tables") },
      { kind: "Ir", label: "Impacto", run: () => go("impact") },
      { kind: "Ir", label: "Gêmeos", run: () => go("twins") },
      { kind: "Ir", label: "Briefing", run: () => go("brief") },
      { kind: "Ir", label: "Colunas", run: () => go("columns") },
      { kind: "Ir", label: t("nav.relations"), run: () => go("relations") },
      { kind: "Ir", label: t("nav.govern"), run: () => go("govern") },
      { kind: "Ação", label: "Alternar tema", run: () => { state.theme = state.theme === "dark" ? "light" : "dark"; applyTheme(); } },
      { kind: "Ação", label: "Exportar SQL organizado", run: exportSQL },
    ];
    const queries = QUERIES.map((item) => ({ kind: "Query", label: item.titulo, hint: item.arquivo, run: () => go("query", { queryId: item.id }) }));
    const tables = (LINEAGE.tables || []).map((t) => ({ kind: "Tabela", label: t.nome, hint: `${t.uso} usos`, run: () => go("table", { tableId: t.nome }) }));
    return [...actions, ...queries, ...tables].filter((item) =>
      !q || `${item.kind} ${item.label} ${item.hint || ""}`.toLowerCase().includes(q)
    ).slice(0, 18);
  };

  let palIndex = 0;
  const openPalette = () => {
    $("palette").hidden = false;
    $("scrim").hidden = false;
    $("palette-input").value = "";
    palIndex = 0;
    drawPalette();
    $("palette-input").focus();
  };
  const closeOverlays = () => {
    $("palette").hidden = true;
    $("help-modal").hidden = true;
    $("scrim").hidden = true;
    $("rail").classList.remove("is-open");
  };
  const drawPalette = () => {
    const items = paletteItems();
    palIndex = Math.max(0, Math.min(palIndex, items.length - 1));
    $("palette-list").innerHTML = items.map((item, i) =>
      `<button class="pal-item ${i===palIndex?"is-on":""}" data-pal="${i}" type="button">
        <span>${esc(item.label)}<small style="display:block">${esc(item.hint || "")}</small></span>
        <small>${esc(item.kind)}</small>
      </button>`
    ).join("") || `<div class="empty">Nenhum resultado</div>`;
    $("palette-list")._items = items;
  };

  function bindSort(tableId) {
    const table = document.getElementById(tableId);
    if (!table) return;
    table.querySelectorAll("th[data-sort]").forEach((th, colIdx) => {
      th.addEventListener("click", () => {
        const tbody = table.tBodies[0];
        const rows = [...tbody.rows];
        const dir = th.dataset.dir === "asc" ? "desc" : "asc";
        table.querySelectorAll("th[data-sort]").forEach((el) => { el.dataset.dir = ""; });
        th.dataset.dir = dir;
        rows.sort((a, b) => {
          const av = a.cells[colIdx]?.innerText.trim() || "";
          const bv = b.cells[colIdx]?.innerText.trim() || "";
          const an = Number(av);
          const bn = Number(bv);
          const cmp = Number.isFinite(an) && Number.isFinite(bn) && av !== "" && bv !== ""
            ? an - bn
            : av.localeCompare(bv, "pt", { numeric: true });
          return dir === "asc" ? cmp : -cmp;
        });
        rows.forEach((row) => tbody.appendChild(row));
      });
    });
  }

  function exportCSV(kind) {
    let header = [];
    let rows = [];
    if (kind === "columns") {
      header = ["coluna", "select", "where", "join", "group", "queries", "pii"];
      rows = COLUMNS.map((c) => [c.nome, c.select || 0, c.where || 0, c.join || 0, c.group || 0, (c.queries || []).length, c.pii ? "sim" : "nao"]);
    } else if (kind === "tables") {
      header = ["tabela", "uso", "queries"];
      rows = (LINEAGE.tables || []).map((t) => [t.nome, t.uso, (t.queries || []).length]);
    } else if (kind === "impact") {
      header = ["tabela", "raio", "risco", "mutacoes", "titulos"];
      rows = (IMPACT || []).map((r) => [r.tabela, r.raio, r.risco, r.mutacoes, (r.titulos || []).join("|")]);
    } else if (kind === "twins") {
      header = ["score", "kind", "arquivo_a", "arquivo_b", "titulo_a", "titulo_b"];
      rows = TWINS.map((p) => [p.score, p.kind, p.arquivo_a, p.arquivo_b, p.titulo_a, p.titulo_b]);
    } else {
      header = ["id", "arquivo", "titulo", "tipo", "dominio", "complexidade", "pii"];
      rows = QUERIES.map((q) => [q.id, q.arquivo, q.titulo, q.tipo, q.dominio, q.complexidade, (q.pii || {}).exposto ? "sim" : "nao"]);
    }
    const csv = [header, ...rows].map((line) => line.map((cell) => `"${String(cell ?? "").replace(/"/g, '""')}"`).join(",")).join("\n");
    download(`acervo-${kind}.csv`, csv, "text/csv");
    toast("CSV exportado");
  }

  function exportSQL() {
    const parts = QUERIES.map((q, i) => `-- ${i + 1}. ${q.titulo}\n-- ${q.arquivo}\n${q.sql}\n;`);
    download("queries_organizadas.sql", parts.join("\n\n"), "text/sql");
    toast("SQL exportado");
  }
  function exportJSON() {
    download("catalogo.json", JSON.stringify(CATALOG, null, 2), "application/json");
    toast("JSON exportado");
  }
  function download(name, content, type) {
    const blob = new Blob([content], { type });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = name;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  document.addEventListener("click", (e) => {
    const routeBtn = e.target.closest("[data-route]");
    if (routeBtn) { go(routeBtn.dataset.route); return; }
    const qBtn = e.target.closest("[data-qid]");
    if (qBtn) { go("query", { queryId: qBtn.dataset.qid }); return; }
    const tBtn = e.target.closest("[data-table]");
    if (tBtn) { go("table", { tableId: tBtn.dataset.table }); return; }
    const folder = e.target.closest("[data-folder]");
    if (folder) { state.pasta = folder.dataset.folder; go("catalog"); return; }
    const domain = e.target.closest("[data-domain]");
    if (domain) { state.dominio = domain.dataset.domain; go("catalog"); return; }
    const tab = e.target.closest("[data-tab]");
    if (tab) { state.tab = tab.dataset.tab; render(); return; }
    const copy = e.target.closest("[data-copy]");
    if (copy) {
      const q = byId(copy.dataset.copy);
      if (q) navigator.clipboard.writeText(state.pretty && q.sql_pretty ? q.sql_pretty : q.sql).then(() => toast("SQL copiado"));
      return;
    }
    const compare = e.target.closest("[data-compare]");
    if (compare) {
      const [a, b] = compare.dataset.compare.split("|");
      go("compare", { compareA: a, compareB: b });
      return;
    }
    const col = e.target.closest("[data-col]");
    if (col) {
      state.search = `col:${col.dataset.col}`;
      go("catalog");
      return;
    }
    const pretty = e.target.closest("[data-pretty]");
    if (pretty) {
      state.pretty = !state.pretty;
      toast(state.pretty ? "SQL formatado" : "SQL original");
      render();
      return;
    }
    const csvBtn = e.target.closest("[data-export-csv]");
    if (csvBtn) {
      exportCSV(csvBtn.dataset.exportCsv);
      return;
    }
    const pal = e.target.closest("[data-pal]");
    if (pal) {
      const items = $("palette-list")._items || [];
      items[Number(pal.dataset.pal)]?.run();
      closeOverlays();
    }
  });

  $("cmd-launch").addEventListener("click", openPalette);
  $("btn-theme").addEventListener("click", () => {
    state.theme = state.theme === "dark" ? "light" : "dark";
    applyTheme();
  });
  $("btn-locale")?.addEventListener("click", () => {
    state.uiLocale = state.uiLocale === "en" ? "pt" : "en";
    localStorage.setItem("acervo-ui-locale", state.uiLocale);
    render();
  });
  $("btn-help").addEventListener("click", () => { $("help-modal").hidden = false; $("scrim").hidden = false; });
  $("help-close").addEventListener("click", closeOverlays);
  $("scrim").addEventListener("click", closeOverlays);
  $("btn-export-sql").addEventListener("click", exportSQL);
  $("btn-export-json").addEventListener("click", exportJSON);
  $("btn-export-csv")?.addEventListener("click", () => exportCSV("queries"));
  $("rail-open").addEventListener("click", () => { $("rail").classList.add("is-open"); $("scrim").hidden = false; });
  $("rail-close").addEventListener("click", closeOverlays);
  $("palette-input").addEventListener("input", () => { palIndex = 0; drawPalette(); });

  document.addEventListener("keydown", (e) => {
    const inField = ["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName);
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); openPalette(); return; }
    if (e.key === "/" && !inField) { e.preventDefault(); openPalette(); return; }
    if (e.key === "Escape") { closeOverlays(); return; }
    if (!$("palette").hidden) {
      const items = $("palette-list")._items || [];
      if (e.key === "ArrowDown") { e.preventDefault(); palIndex += 1; drawPalette(); }
      if (e.key === "ArrowUp") { e.preventDefault(); palIndex -= 1; drawPalette(); }
      if (e.key === "Enter") { e.preventDefault(); items[palIndex]?.run(); closeOverlays(); }
      return;
    }
    if (inField) return;
    if (e.key === "1") go("home");
    if (e.key === "2") go("catalog");
    if (e.key === "3") go("lineage");
    if (e.key === "4") go("tables");
    if (e.key === "5") go("impact");
    if (e.key === "6") go("twins");
    if (e.key === "7") go("brief");
    if (e.key === "8") go("columns");
    if (e.key === "9") go("relations");
    if (e.key === "0") go("govern");
    if (e.key === "t" || e.key === "T") { state.theme = state.theme === "dark" ? "light" : "dark"; applyTheme(); }
    if (e.key === "?") { $("help-modal").hidden = false; $("scrim").hidden = false; }
  });

  if (!/MAC/i.test(navigator.platform || "")) {
    const kbd = document.querySelector(".cmd-launch kbd");
    if (kbd) kbd.textContent = "Ctrl K";
  }

  window.addEventListener("popstate", parseHash);
  applyTheme();
  parseHash();
})();
