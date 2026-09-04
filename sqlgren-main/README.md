# Acervo 6

The team's canonical SQL archive — a **static observatory** you can put in a Friday email.

Inventory, column lineage, blast radius, twins, PII, a manager briefing, PT/EN, and a shareable HTML.  
**No SQL execution. No dbt. No warehouse.**

O repositório ainda se chama `sqlgren`. O produto é **Acervo**.

---

## Why this can be sold

Acervo does not compete with OpenMetadata, DataHub or dbt. Those need a warehouse, connectors, and a platform team.

Acervo wins when the truth is a **folder of `.sql`**:

- a consultancy delivering official health / APS indicators
- a BI team that inherited scripts and lost the author
- audit / internal control that wants evidence without production access
- any company that must share SQL documentation **without leaking CPF, CNS, email, tokens**

The artifact is one HTML file (plus JSON, Markdown, ZIP). That is the product.

---

## What is new in 6.0

- Native **pt / en** catalog (`--locale en`) — SQL stays as written
- **`--redact-pii`** masks emails, national IDs, secrets in exported SQL
- Cloud studio: locale, PII mask (on by default), optional **PIN**, **ZIP** pack
- Governance view in the SPA (shortcut `0`)
- Honest Community / Pro / Team packaging — Pro is not billed yet
- Same engine: CLL, twins, cascade, implied keys, SQLFluff-lite smells, `--ask` / `--table` / `--baseline`

---

## CLI

```bash
python src/cli.py queries --title "Acervo APS" --open
python src/cli.py queries --locale en --redact-pii -o output
python src/cli.py --input queries --check --pr-comment
python src/cli.py queries --target-dialect snowflake -o output
python src/cli.py queries --ask "table:cidadao col:cns"
python src/cli.py queries --table tb_dim_tempo
python src/cli.py queries --baseline output/catalogo.json --pr-comment
```

Open `output/consultas.html`.

Search: `table:cidadao` · `col:cns` · `tag:CTE` · `tipo:UPDATE`  
Shortcuts `1–9` · `0` governance · `Ctrl+K` · `T` theme · `PT/EN` chrome.

CI: `.pre-commit-config.yaml` runs `--check` on `.sql` changes. Exit `2` = critical smell.

## SaaS (local studio)

```bash
npm start
```

Opens `http://127.0.0.1:8787` — bilingual landing, upload, APS demo, PIN, ZIP.  
Public URL: `/p/{id}` · JSON: `/p/{id}/catalog.json` · pack: `/p/{id}.zip` · health: `/health`.

Demo catalogs are generated **redacted**. That is the default for anything you would send to a client.

## Tests

```bash
pip install -r requirements.txt pytest
pytest tests -q
```

Node assemble (no Python required):

```bash
npm run build
```

---

## Commercial note

Community is MIT and complete for a consultancy delivery.  
Pro ($29/mo) and Team ($99/mo) on the landing are **product intent**, not a charge. No Stripe yet.

If you sell Acervo as a service, the value is the Friday artifact: HTML + briefing + redacted SQL + blast radius. Not another catalog platform.

## License

MIT · Alacoque
