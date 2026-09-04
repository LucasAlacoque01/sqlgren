import { buildCatalogFromEntries, renderHtml } from "../src/engine.mjs";

const entries = [{
  path: "t.sql",
  sql: "SELECT email FROM t WHERE email = 'a@b.com' AND cpf = '123.456.789-09'",
}];
const catalog = buildCatalogFromEntries(entries, "Smoke", { locale: "en", redact: true });
const html = renderHtml(catalog);
const ok = [
  catalog.meta.locale === "en",
  catalog.meta.redacted === true,
  /warehouse/i.test(catalog.meta.pitch),
  catalog.queries[0].sql.includes("REDACTED"),
  !catalog.queries[0].sql.includes("a@b.com"),
  /this week/i.test(catalog.briefing.headline),
  html.includes('lang="en"'),
  html.includes("nav.govern"),
  html.includes("btn-locale"),
];
if (ok.some((v) => !v)) {
  console.error("smoke failed", ok, catalog.meta, catalog.queries[0].sql);
  process.exit(1);
}
console.log("smoke ok", catalog.meta.locale, catalog.meta.version, catalog.stats.pii);
