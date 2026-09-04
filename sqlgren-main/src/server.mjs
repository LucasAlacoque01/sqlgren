import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { ROOT, buildCatalogFromEntries, entriesFromDir, renderHtml } from "./engine.mjs";

const PUBLIC = path.join(ROOT, "saas", "public");
const DATA = path.join(ROOT, "data", "projects");
const PORT = Number(process.env.PORT || 8787);
const MAX_FILES = 80;
const MAX_BYTES = 400_000;
const VERSION = "6.0.0";

fs.mkdirSync(DATA, { recursive: true });

function send(res, code, body, type, extra = {}) {
  const raw = Buffer.isBuffer(body) ? body : Buffer.from(body);
  const headers = {
    "Content-Type": type,
    "Content-Length": raw.length,
    ...extra,
  };
  const cookie = res.getHeader("Set-Cookie");
  if (cookie) headers["Set-Cookie"] = cookie;
  res.writeHead(code, headers);
  res.end(raw);
}

function json(res, code, body) {
  send(res, code, JSON.stringify(body), "application/json; charset=utf-8");
}

function html(res, code, body) {
  send(res, code, body, "text/html; charset=utf-8");
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    req.on("data", (c) => {
      size += c.length;
      if (size > 6_000_000) {
        reject(new Error("payload grande demais"));
        req.destroy();
        return;
      }
      chunks.push(c);
    });
    req.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    req.on("error", reject);
  });
}

function workspace(req, res) {
  const cookie = String(req.headers.cookie || "");
  const found = cookie.match(/acervo_ws=([a-f0-9-]{8,})/i);
  if (found) return found[1];
  const id = crypto.randomUUID();
  res.setHeader("Set-Cookie", `acervo_ws=${id}; Path=/; HttpOnly; SameSite=Lax; Max-Age=31536000`);
  return id;
}

function hashPin(pin) {
  return crypto.createHash("sha256").update(String(pin)).digest("hex");
}

function readMeta(id) {
  const file = path.join(DATA, id, "meta.json");
  if (!fs.existsSync(file)) return null;
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch {
    return null;
  }
}

function pinOk(meta, url, req) {
  if (!meta?.pin_hash) return true;
  const q = url.searchParams.get("pin");
  if (q && hashPin(q) === meta.pin_hash) return true;
  const cookie = String(req.headers.cookie || "");
  return new RegExp(`acervo_pin_${meta.id}=1`).test(cookie);
}

function unlockPage(id, locale = "pt") {
  const en = String(locale).startsWith("en");
  return `<!doctype html><html lang="${en ? "en" : "pt-BR"}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Acervo</title>
  <style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#07080c;color:#eef2f8;font-family:IBM Plex Sans,system-ui,sans-serif}form{width:min(420px,calc(100% - 40px));background:#12151d;border:1px solid rgba(255,255,255,.08);border-radius:18px;padding:28px}h1{font-family:Syne,sans-serif;margin:0 0 8px}p{color:#8d95a8}input{width:100%;padding:10px 12px;border-radius:10px;border:1px solid rgba(255,255,255,.08);background:#0c0e14;color:#eef2f8}button{margin-top:14px;background:#5eead4;color:#04201c;border:0;border-radius:10px;padding:10px 16px;font-weight:700;cursor:pointer}.err{color:#fb7185;min-height:1.2em}</style></head>
  <body><form method="post" action="/p/${id}/unlock"><h1>Acervo</h1><p>${en ? "This catalog is PIN-protected." : "Este catálogo está protegido por PIN."}</p>
  <input name="pin" type="password" maxlength="32" placeholder="PIN" autofocus>
  <div class="err"></div><button type="submit">${en ? "Unlock" : "Desbloquear"}</button></form></body></html>`;
}

function crc32(buf) {
  let c = ~0;
  for (const b of buf) {
    c ^= b;
    for (let i = 0; i < 8; i += 1) c = (c >>> 1) ^ (0xedb88320 & -(c & 1));
  }
  return ~c >>> 0;
}

function zipStore(files) {
  const locals = [];
  const centrals = [];
  let offset = 0;
  for (const file of files) {
    const name = Buffer.from(file.name, "utf8");
    const data = Buffer.isBuffer(file.data) ? file.data : Buffer.from(file.data);
    const crc = crc32(data);
    const local = Buffer.alloc(30);
    local.writeUInt32LE(0x04034b50, 0);
    local.writeUInt16LE(20, 4);
    local.writeUInt32LE(crc, 14);
    local.writeUInt32LE(data.length, 18);
    local.writeUInt32LE(data.length, 22);
    local.writeUInt16LE(name.length, 26);
    locals.push(local, name, data);
    const cen = Buffer.alloc(46);
    cen.writeUInt32LE(0x02014b50, 0);
    cen.writeUInt16LE(20, 4);
    cen.writeUInt16LE(20, 6);
    cen.writeUInt32LE(crc, 16);
    cen.writeUInt32LE(data.length, 20);
    cen.writeUInt32LE(data.length, 24);
    cen.writeUInt16LE(name.length, 28);
    cen.writeUInt32LE(offset, 42);
    centrals.push(cen, name);
    offset += 30 + name.length + data.length;
  }
  const central = Buffer.concat(centrals);
  const end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0);
  end.writeUInt16LE(files.length, 8);
  end.writeUInt16LE(files.length, 10);
  end.writeUInt32LE(central.length, 12);
  end.writeUInt32LE(offset, 16);
  return Buffer.concat([...locals, central, end]);
}

function listProjects(ws) {
  return fs.readdirSync(DATA, { withFileTypes: true })
    .filter((e) => e.isDirectory())
    .map((e) => {
      const meta = readMeta(e.name);
      if (!meta || meta.workspace !== ws) return null;
      const { pin_hash, ...safe } = meta;
      return { ...safe, locked: Boolean(pin_hash) };
    })
    .filter(Boolean)
    .sort((a, b) => (b.created_at || "").localeCompare(a.created_at || ""));
}

function landing() {
  return fs.readFileSync(path.join(PUBLIC, "index.html"), "utf8");
}

function readCatalog(id) {
  const file = path.join(DATA, id, "catalogo.json");
  if (!fs.existsSync(file)) return null;
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch {
    return null;
  }
}

function briefingMarkdown(catalog) {
  const brief = catalog.briefing || {};
  return [
    `# ${brief.headline || "Acervo"}`,
    "",
    brief.risco_imediato || "",
    "",
    ...(brief.achados || []).map((item) => `- ${item}`),
    "",
    ...(brief.proximos || []).map((item) => `- ${item}`),
    "",
  ].join("\n");
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);
  const ws = workspace(req, res);

  try {
    if (req.method === "GET" && url.pathname === "/") {
      return html(res, 200, landing());
    }

    if (req.method === "GET" && url.pathname === "/api/projects") {
      return json(res, 200, { projects: listProjects(ws) });
    }

    const catalogApi = url.pathname.match(/^\/api\/projects\/([a-f0-9-]{8,})\/catalog$/i);
    if (req.method === "GET" && catalogApi) {
      const meta = readMeta(catalogApi[1]);
      if (!meta) return json(res, 404, { erro: "catálogo não encontrado" });
      if (!pinOk(meta, url, req)) return json(res, 401, { erro: "PIN necessário" });
      const catalog = readCatalog(catalogApi[1]);
      if (!catalog) return json(res, 404, { erro: "catálogo não encontrado" });
      return json(res, 200, catalog);
    }

    if (req.method === "POST" && url.pathname === "/api/demo") {
      const body = JSON.parse(await readBody(req) || "{}");
      const locale = String(body.locale || url.searchParams.get("locale") || "pt");
      const entries = entriesFromDir(path.join(ROOT, "queries"));
      return createProject(res, ws, locale.startsWith("en") ? "APS demo" : "Demo APS", entries, {
        locale,
        redact: true,
      });
    }

    if (req.method === "POST" && url.pathname === "/api/projects") {
      const body = JSON.parse(await readBody(req) || "{}");
      const title = String(body.title || "Acervo").slice(0, 80);
      const files = Array.isArray(body.files) ? body.files : [];
      if (!files.length) return json(res, 400, { erro: "Envie ao menos um arquivo .sql" });
      if (files.length > MAX_FILES) return json(res, 400, { erro: `Máximo de ${MAX_FILES} arquivos no plano atual` });
      const entries = [];
      for (const file of files) {
        const sql = String(file.sql || "");
        if (Buffer.byteLength(sql) > MAX_BYTES) return json(res, 400, { erro: `${file.path} excede o limite` });
        if (!String(file.path || "").toLowerCase().endsWith(".sql")) continue;
        entries.push({ path: String(file.path || "query.sql").replace(/^\/+/, ""), sql });
      }
      if (!entries.length) return json(res, 400, { erro: "Nenhum .sql válido" });
      return createProject(res, ws, title, entries, {
        locale: body.locale || "pt",
        redact: Boolean(body.redact_pii ?? true),
        pin: body.pin,
      });
    }

    const unlock = url.pathname.match(/^\/p\/([a-f0-9-]{8,})\/unlock$/i);
    if (req.method === "POST" && unlock) {
      const meta = readMeta(unlock[1]);
      if (!meta) return html(res, 404, "<h1>Not found</h1>");
      const raw = await readBody(req);
      const pin = String(new URLSearchParams(raw).get("pin") || JSON.parse(raw || "{}").pin || "");
      if (!meta.pin_hash || hashPin(pin) !== meta.pin_hash) {
        return html(res, 401, unlockPage(unlock[1], meta.locale));
      }
      res.setHeader("Set-Cookie", `acervo_pin_${meta.id}=1; Path=/; HttpOnly; SameSite=Lax; Max-Age=86400`);
      res.writeHead(302, { Location: `/p/${meta.id}` });
      return res.end();
    }

    const pubZip = url.pathname.match(/^\/p\/([a-f0-9-]{8,})\.zip$/i);
    if (req.method === "GET" && pubZip) {
      const meta = readMeta(pubZip[1]);
      if (!meta) return json(res, 404, { erro: "não encontrado" });
      if (!pinOk(meta, url, req)) return html(res, 401, unlockPage(pubZip[1], meta.locale));
      const catalog = readCatalog(pubZip[1]);
      const htmlFile = path.join(DATA, pubZip[1], "consultas.html");
      if (!catalog || !fs.existsSync(htmlFile)) return json(res, 404, { erro: "não encontrado" });
      const archive = zipStore([
        { name: "consultas.html", data: fs.readFileSync(htmlFile) },
        { name: "catalogo.json", data: JSON.stringify(catalog, null, 2) },
        { name: "BRIEFING.md", data: briefingMarkdown(catalog) },
      ]);
      return send(res, 200, archive, "application/zip", {
        "Content-Disposition": `attachment; filename="acervo-${pubZip[1].slice(0, 8)}.zip"`,
      });
    }

    const pubJson = url.pathname.match(/^\/p\/([a-f0-9-]{8,})\/catalog\.json$/i);
    if (req.method === "GET" && pubJson) {
      const meta = readMeta(pubJson[1]);
      if (!meta) return json(res, 404, { erro: "não encontrado" });
      if (!pinOk(meta, url, req)) return json(res, 401, { erro: "PIN necessário" });
      const catalog = readCatalog(pubJson[1]);
      if (!catalog) return json(res, 404, { erro: "não encontrado" });
      return json(res, 200, catalog);
    }

    const pub = url.pathname.match(/^\/p\/([a-f0-9-]{8,})$/i);
    if (req.method === "GET" && pub) {
      const meta = readMeta(pub[1]);
      if (!meta) return html(res, 404, "<h1>Projeto não encontrado</h1>");
      if (!pinOk(meta, url, req)) return html(res, 401, unlockPage(pub[1], meta.locale));
      const file = path.join(DATA, pub[1], "consultas.html");
      if (!fs.existsSync(file)) return html(res, 404, "<h1>Projeto não encontrado</h1>");
      return html(res, 200, fs.readFileSync(file, "utf8"));
    }

    if (req.method === "GET" && url.pathname === "/health") {
      return json(res, 200, {
        ok: true,
        product: "Acervo",
        version: VERSION,
        edition: "community",
        capabilities: ["static-sql", "pii-redact", "i18n", "pin-share", "zip-pack", "ci-check"],
      });
    }

    return json(res, 404, { erro: "não encontrado" });
  } catch (err) {
    return json(res, 500, { erro: String(err.message || err) });
  }
});

function createProject(res, ws, title, entries, options = {}) {
  const id = crypto.randomUUID();
  const locale = String(options.locale || "pt").toLowerCase().startsWith("en") ? "en" : "pt";
  const redact = options.redact !== false;
  const catalog = buildCatalogFromEntries(entries, title, { locale, redact });
  const dir = path.join(DATA, id);
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, "consultas.html"), renderHtml(catalog));
  fs.writeFileSync(path.join(dir, "catalogo.json"), JSON.stringify(catalog));
  const pin = String(options.pin || "").trim();
  const meta = {
    id,
    title,
    workspace: ws,
    created_at: new Date().toISOString(),
    queries: catalog.stats.queries,
    saude: catalog.stats.saude,
    pii: catalog.stats.pii,
    locale,
    redacted: Boolean(catalog.meta.redacted),
    url: `/p/${id}`,
    zip: `/p/${id}.zip`,
  };
  if (pin) meta.pin_hash = hashPin(pin);
  fs.writeFileSync(path.join(dir, "meta.json"), JSON.stringify(meta, null, 2));
  const { pin_hash, ...safe } = meta;
  return json(res, 201, { ...safe, locked: Boolean(pin_hash) });
}

server.listen(PORT, "127.0.0.1", () => {
  console.log(`Acervo Cloud  http://127.0.0.1:${PORT}`);
});
