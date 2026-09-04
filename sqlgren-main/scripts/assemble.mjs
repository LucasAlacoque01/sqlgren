import fs from "node:fs";
import path from "node:path";
import { ROOT, buildCatalogFromEntries, entriesFromDir, renderHtml } from "./engine.mjs";

const queriesDir = path.join(ROOT, "queries");
const outputDir = path.join(ROOT, "output");
const entries = entriesFromDir(queriesDir);
const catalog = buildCatalogFromEntries(entries, "Observatório APS");
const html = renderHtml(catalog);

fs.mkdirSync(outputDir, { recursive: true });
fs.writeFileSync(path.join(outputDir, "consultas.html"), html);
fs.writeFileSync(path.join(outputDir, "catalogo.json"), JSON.stringify(catalog, null, 2));
fs.writeFileSync(path.join(outputDir, "queries_organizadas.sql"), catalog.queries.map((q, i) => `-- ${i + 1}. ${q.titulo}\n-- ${q.arquivo}\n${q.sql}\n;`).join("\n\n"));
fs.writeFileSync(path.join(outputDir, "BRIEFING.md"), `# ${catalog.briefing.headline}\n\n${catalog.briefing.risco_imediato}\n`);
console.log(`Acervo assemble: ${catalog.queries.length} queries → output/consultas.html`);
